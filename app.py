import os
import re

# 정규식 정의
INTERFACE_REGEX = re.compile(
    r"interface\s+(\w+)\s*(?:implements\s+([\w\s&]+))?\s*\{([\s\S]+?)\}", re.MULTILINE
)
TYPE_REGEX = re.compile(
    r"type\s+(\w+)\s+implements\s+([\w\s&]+)(.*)\{([\s\S]+?)\}", re.MULTILINE
)
UNION_REGEX = re.compile(r"(extend\s+)?union\s+(\w+)\s*(?:=\s*(.*))?")
ENUM_REGEX = re.compile(r"enum\s+(\w+)\s*\{([\s\S]+?)\}", re.MULTILINE)

# 입력 폴더 및 출력 폴더 경로
input_folder = "./template"
output_folder = "./schemas"


def parse_interface_content(content):
    """인터페이스의 필드와 어노테이션을 파싱"""
    interfaces = {}
    for match in INTERFACE_REGEX.finditer(content):
        interface_name = match.group(1)
        implemented_interfaces = (
            match.group(2).strip().split(" & ") if match.group(2) else []
        )
        fields = match.group(3).strip()
        interfaces[interface_name] = (implemented_interfaces, fields)
    return interfaces


def parse_type_content(content):
    """타입 정의를 파싱"""

    types = {}
    for match in TYPE_REGEX.finditer(content):
        type_name = match.group(1)
        implemented_interfaces = match.group(2).strip().split(" & ")
        node_annotation = match.group(3)
        fields = match.group(4).strip()
        types[type_name] = (implemented_interfaces, node_annotation, fields)
    return types


def parse_union_content(content):
    """유니언 정의를 파싱"""
    unions = {"extend": {}, "normal": {}}
    for match in UNION_REGEX.finditer(content):
        union_name = match.group(2)
        union_types = match.group(3).strip() if match.group(3) else ""
        if match.group(1):
            unions["extend"][union_name] = union_types
        else:
            unions["normal"][union_name] = union_types
    return unions


def parse_enum_content(content):
    """enum 정의를 파싱"""
    enums = {}
    for match in ENUM_REGEX.finditer(content):
        enum_name = match.group(1)
        enum_values = match.group(2).strip()
        enums[enum_name] = enum_values
    return enums


def process_annotations(fields):
    """# @ 어노테이션을 @로 변경하고 괄호 안의 #을 제거"""
    processed_fields = []
    open_parentheses_count = 0
    for field in fields.split("\n"):
        # # @로 시작하는 어노테이션 처리
        processed_field = re.sub(r"#\s*@", "@", field.strip())

        # 괄호의 개수 체크
        open_parentheses_count += processed_field.count("(")

        # 괄호 내부에 있을 경우 # 제거
        if open_parentheses_count > 0:
            processed_field = re.sub(r"#\s?", "", processed_field)
        open_parentheses_count -= processed_field.count(")")

        if processed_field:
            processed_fields.append(processed_field)

    return "\n    ".join(processed_fields)


def merge_fields(base_fields, additional_fields, from_interface=None):
    """기본 필드에 추가 필드를 병합하며 추가된 필드는 주석 처리 (기존 필드 덮어쓰기 방지)"""
    base_fields_dict = {}
    for field in base_fields.split("\n"):
        if field.strip():
            field_name = field.split(":")[0].strip()
            base_fields_dict[field_name] = field.strip()

    merged_fields = base_fields.strip()

    if from_interface:
        merged_fields += f"\n    # from {from_interface}"

    for field in additional_fields.split("\n"):
        field_name = field.split(":")[0].strip()
        if field_name and field_name not in base_fields_dict:
            merged_fields += f"\n    {field.strip()}"
        elif field_name in base_fields_dict:
            # Existing field, do not overwrite
            merged_fields = merged_fields.replace(
                f"\n    {field_name}:", f"\n    {field_name}:"
            )

    return merged_fields


def get_all_fields(implemented_interfaces, interfaces):
    """재귀적으로 모든 상속된 인터페이스의 필드를 가져옴"""
    merged_fields = ""
    for interface in implemented_interfaces:
        if interface in interfaces:
            parent_interfaces, fields = interfaces[interface]
            # 부모 인터페이스의 필드를 재귀적으로 병합
            merged_fields = merge_fields(
                get_all_fields(parent_interfaces, interfaces), merged_fields
            )
            merged_fields = merge_fields(
                merged_fields,
                fields,
                from_interface=interface,
            )
    return merged_fields


def collect_all_definitions(input_folder):
    """모든 인터페이스, 타입, 유니언, enum 정의를 한 번에 수집"""
    interfaces = {}
    types = {}
    unions = {"extend": {}, "normal": {}}
    enums = {}

    for dirpath, _, filenames in os.walk(input_folder):
        for filename in filenames:
            if filename.endswith(".template.gql"):
                input_path = os.path.join(dirpath, filename)
                with open(input_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    # 인터페이스, 타입, 유니언, enum 모두 수집
                    interfaces.update(parse_interface_content(content))
                    types.update(parse_type_content(content))
                    unions_data = parse_union_content(content)
                    unions["extend"].update(unions_data["extend"])
                    unions["normal"].update(unions_data["normal"])
                    enums.update(parse_enum_content(content))

    return interfaces, types, unions, enums


def process_template_file(input_path, output_path, interfaces, types, unions, enums):
    """템플릿 파일을 처리하고 결과를 출력"""
    with open(input_path, "r", encoding="utf-8") as file:
        content = file.read()

    output_content = ""
    if "union" in content:
        # 유니언 파일 처리
        unions_parsed = parse_union_content(content)
        for union_name, union_types in unions_parsed["normal"].items():
            if union_types:
                output_content += f"union {union_name} = {union_types}\n"
            else:
                output_content += f"union {union_name}\n"
        for union_name, union_types in unions_parsed["extend"].items():
            output_content += f"extend union {union_name} = {union_types}\n"

    if "enum" in content:
        # enum 파일 처리
        enums_parsed = parse_enum_content(content)
        for enum_name, enum_values in enums_parsed.items():
            output_content += f"enum {enum_name} {{\n    {enum_values}\n}}\n\n"
    if "interface" in content:
        # 인터페이스 파일 처리
        interfaces_parsed = parse_interface_content(content)
        for interface_name, (
            implemented_interfaces,
            fields,
        ) in interfaces_parsed.items():
            # implements된 인터페이스의 필드를 병합
            merged_fields = get_all_fields(implemented_interfaces, interfaces)
            merged_fields = merge_fields(fields, merged_fields)
            output_content += f"interface {interface_name}"
            if implemented_interfaces:
                output_content += f' implements {" & ".join(implemented_interfaces)}'
            output_content += " {\n"
            if merged_fields:
                output_content += f"    {merged_fields}\n"
            output_content += "}}\n\n"

    if "type" in content:
        # 타입 파일 처리
        types_parsed = parse_type_content(content)
        for type_name, (
            implemented_interfaces,
            node_annotation,
            fields,
        ) in types_parsed.items():
            # implements된 인터페이스의 필드를 병합
            merged_fields = get_all_fields(implemented_interfaces, interfaces)
            merged_fields = merge_fields(fields, merged_fields)
            # 어노테이션을 병합 후 처리
            merged_fields = process_annotations(merged_fields)
            output_content += f'type {type_name} implements {" & ".join(implemented_interfaces)} {node_annotation}{{\n'
            output_content += f"    {merged_fields}\n"
            output_content += "}\n\n"

    # 출력 파일 작성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(output_content)


def process_all_templates(input_folder, output_folder):
    """input 폴더의 모든 템플릿 파일을 처리하여 output 폴더에 작성"""
    # 모든 인터페이스, 타입, 유니언, enum 정의를 한 번에 수집
    interfaces, types, unions, enums = collect_all_definitions(input_folder)

    # 수집된 정의를 기반으로 각 파일 처리
    for dirpath, _, filenames in os.walk(input_folder):
        for filename in filenames:
            if filename.endswith(".template.gql"):
                input_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(input_path, input_folder)
                output_path = os.path.join(
                    output_folder, relative_path.replace(".template.gql", ".gql")
                )

                process_template_file(
                    input_path, output_path, interfaces, types, unions, enums
                )


# 실행
process_all_templates(input_folder, output_folder)
