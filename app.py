import os
import re

INTERFACE_REGEX = re.compile(
    r"interface\s+(\w+)\s*(?:implements\s+([\w\s&]+))?\s*\{([\s\S]+?)\}", re.MULTILINE
)
TYPE_REGEX = re.compile(
    r"type\s+(\w+\s+)(?:implements\s+([\w\s&]+))?((?:\s*@[\w]+(?:\([^)]*\))?)*\s+)?\{([\s\S]+?)\}",
    re.MULTILINE,
)
UNION_REGEX = re.compile(r"(extend\s+)?union\s+(\w+)\s*(?:=\s*(.*))?")
ENUM_REGEX = re.compile(r"enum\s+(\w+)\s*\{([\s\S]+?)\}", re.MULTILINE)
INPUT_REGEX = re.compile(r"input\s+(\w+)\s*\{([\s\S]+?)\}", re.MULTILINE)

NEW_LINE = "\n"
DOUBLE_LINE = NEW_LINE * 2
INDENT = " " * 4
NEW_INDENT = NEW_LINE + INDENT


def parse_interface_content(content):
    parsed_interfaces = {}
    for match in INTERFACE_REGEX.finditer(content):
        interface_name = match.group(1)
        implemented_interfaces = (
            match.group(2).strip().split(" & ") if match.group(2) else []
        )
        fields = match.group(3).strip()
        parsed_interfaces[interface_name] = (implemented_interfaces, fields)
    return parsed_interfaces


def parse_type_content(content):
    types = {}
    for match in TYPE_REGEX.finditer(content):
        type_name = match.group(1)
        implemented_interfaces = (
            match.group(2).strip().split(" & ") if match.group(2) else []
        )
        node_annotation = match.group(3) if match.group(3) else ""
        fields = match.group(4).strip()
        types[type_name] = (implemented_interfaces, node_annotation, fields)
    return types


def parse_union_content(content):
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
    enums = {}
    for match in ENUM_REGEX.finditer(content):
        enum_name = match.group(1)
        enum_values = match.group(2).strip()
        enums[enum_name] = enum_values
    return enums


def parse_input_content(content):
    inputs = {}
    for match in INPUT_REGEX.finditer(content):
        input_name = match.group(1)
        input_values = match.group(2).strip()
        inputs[input_name] = input_values
    return inputs


def process_annotations(fields):
    """파싱규칙: `# @Directive` 주석을 제거하고, 멀티라인 처리(@이름(멀티라인 내용) Directives에서 #을 제거)"""
    processed_fields = []
    open_parentheses_count = 0
    open_parentheses = False

    for field in fields.split(NEW_LINE):
        processed_field = re.sub(r"#\s*@", "@", field.strip())
        open_parentheses_count += processed_field.count("(")

        if "@" in field.strip() and open_parentheses_count > 0:
            open_parentheses = True

        if open_parentheses and open_parentheses_count > 0:
            processed_field = re.sub(r"^\s*#\s?", "", processed_field)

        open_parentheses_count -= processed_field.count(")")

        if open_parentheses_count == 0:
            open_parentheses = False

        if processed_field:
            processed_fields.append(processed_field)

    return NEW_INDENT.join(processed_fields)


def merge_fields(base_fields, additional_fields, from_interface=None):
    """기본 필드에 super 필드를 병합(기존 필드 덮어쓰기 방지)"""
    base_fields_dict = {}
    for field in base_fields.split(NEW_LINE):
        if field.strip():
            field_name = field.split(":")[0].strip()
            base_fields_dict[field_name] = field.strip()

    merged_fields = base_fields.strip()

    if from_interface:
        merged_fields += f"{NEW_INDENT}# from {from_interface}"

    for field in additional_fields.split(NEW_LINE):
        field_name = field.split(":")[0].strip()
        if "#" in field_name:
            merged_fields += f"{NEW_INDENT}{field.strip()}"
        elif field_name and field_name not in base_fields_dict:
            merged_fields += f"{NEW_INDENT}{field.strip()}"

    return merged_fields


def get_all_fields(implemented_interfaces, interfaces):
    """모든 상속된 인터페이스의 필드 재귀 수집"""
    merged_fields = ""
    for interface in implemented_interfaces:
        if interface in interfaces:
            parent_interfaces, fields = interfaces[interface]
            merged_fields = merge_fields(
                get_all_fields(parent_interfaces, interfaces), merged_fields
            )
            merged_fields = merge_fields(
                merged_fields,
                fields,
                from_interface=interface,
            )
    return merged_fields


def get_all_interfaces(implemented_interfaces, interfaces, accumulated_interfaces=None):
    """모든 상속된 인터페이스 재귀 수집"""
    if accumulated_interfaces is None:
        accumulated_interfaces = []

    for interface in implemented_interfaces:
        if interface not in accumulated_interfaces:
            if interface in interfaces:
                parent_interfaces, _ = interfaces[interface]
                get_all_interfaces(
                    parent_interfaces,
                    interfaces,
                    accumulated_interfaces,
                )
            accumulated_interfaces.append(interface)

    return accumulated_interfaces[::-1]


def collect_all_definitions(input_folder):
    """전체 스키마 수집."""
    interfaces = {}
    types = {}
    unions = {"extend": {}, "normal": {}}
    enums = {}
    inputs = {}

    for dirpath, _, filenames in os.walk(input_folder):
        for filename in filenames:
            if filename.endswith(".template.gql"):
                input_path = os.path.join(dirpath, filename)
                with open(input_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    interfaces.update(parse_interface_content(content))
                    types.update(parse_type_content(content))
                    unions_data = parse_union_content(content)
                    unions["extend"].update(unions_data["extend"])
                    unions["normal"].update(unions_data["normal"])
                    enums.update(parse_enum_content(content))
                    inputs.update(parse_input_content(content))

    return {
        "interfaces": interfaces,
        "types": types,
        "unions": unions,
        "enums": enums,
        "inputs": inputs,
    }


def process_template_file(input_path, output_path, schemas):
    """템플릿 파일을 처리하고 결과를 출력"""
    with open(input_path, "r", encoding="utf-8") as file:
        content = file.read()

    output_content = ""
    if "union" in content:
        unions_parsed = parse_union_content(content)
        for union_name, union_types in unions_parsed["normal"].items():
            output_content += f"union {union_name}"
            output_content += f" = {union_types}\n" if union_types else "\n"
        for union_name, union_types in unions_parsed["extend"].items():
            output_content += f"extend union {union_name} = {union_types}\n"

    if "enum" in content:
        enums_parsed = parse_enum_content(content)
        for enum_name, enum_values in enums_parsed.items():
            output_content += f"enum {enum_name} {{{NEW_INDENT}{enum_values}\n}}\n\n"

    if "input" in content:
        input_parsed = parse_input_content(content)
        for input_name, input_values in input_parsed.items():
            output_content += f"input {input_name} {{{NEW_INDENT}{input_values}\n}}\n\n"

    if "interface" in content:
        interfaces_parsed = parse_interface_content(content)
        for interface_name, (
            implemented_interfaces,
            fields,
        ) in interfaces_parsed.items():
            all_interfaces = get_all_interfaces(
                implemented_interfaces, schemas.get("interfaces")
            )
            merged_fields = get_all_fields(
                implemented_interfaces, schemas.get("interfaces")
            )
            merged_fields = merge_fields(fields, merged_fields)
            output_content += f"interface {interface_name}"
            if implemented_interfaces:
                output_content += f' implements {" & ".join(all_interfaces)}'
            output_content += " {\n"
            if merged_fields:
                output_content += f"{INDENT}{merged_fields}\n"
            output_content += "}\n\n"

    if "type" in content:
        types_parsed = parse_type_content(content)
        # print(types_parsed) if "ObjectOrderedCollection" in content else None
        for type_name, (
            implemented_interfaces,
            node_annotation,
            fields,
        ) in types_parsed.items():
            all_interfaces = get_all_interfaces(
                implemented_interfaces, schemas.get("interfaces")
            )
            merged_fields = get_all_fields(
                implemented_interfaces, schemas.get("interfaces")
            )
            merged_fields = merge_fields(fields, merged_fields)
            merged_fields = process_annotations(merged_fields)
            output_content += f"type {type_name} "
            if len(all_interfaces) > 0:
                output_content += f'implements {" & ".join(all_interfaces)} '
            output_content += f"{node_annotation or ''}{{\n"
            output_content += f"{INDENT}{merged_fields}\n"
            output_content += "}\n\n"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(output_content)


def process_all_templates(input_folder, output_folder):
    """input 폴더의 모든 템플릿 파일을 처리하여 output 폴더에 작성"""
    # interfaces, types, unions, enums
    schemas = collect_all_definitions(input_folder)
    for dirpath, _, filenames in os.walk(input_folder):
        for filename in filenames:
            if filename.endswith(".template.gql"):
                input_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(input_path, input_folder)
                output_path = os.path.join(
                    output_folder, relative_path.replace(".template.gql", ".gql")
                )

                process_template_file(input_path, output_path, schemas)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, "template")
    output_folder = os.path.join(script_dir, "schemas")
    try:
        process_all_templates(input_folder, output_folder)

    except Exception as err:
        print(err)
