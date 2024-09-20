
- ./template 폴더의 모든 gql 읽어서 implements 구조대로 field 채워주는 코드. 
- 현재 지원되는 object keyword: type, interface, enum, union, input


# Usage

- ./template 폴더 내에 `~.template.gql` 로 파일을 작성합니다. 
- implements는 가장 인접한 상위 interface만 작성합니다. 
- type의 Directives 는 동일하게 작성합니다.(inline 지향)
- ./schemas 폴더로 export 됩니다.

## export 규칙
- 폴더 구조 유지됩니다. 
- 블록 내 주석(type, interface 블록 외부 주석은 삭제됨), enum, union은 그대로 복사합니다. 
- inline 주석은 지양합니다. (interface Directives for type 때문에 파싱 오류 가능성 있음.)
- 중복된 field는 하위 type 값이 유지됩니다.(override)

# Issue
- body 내 json 타입 property가 있는 directive 파싱 오류 (마지막 `}` 뒤로 잘림.)
    - 선언부(@node, @fulltext)에서는 상관없음. 
- interface에서 필드의 directive를 줄바꿈해서 작성한 후 Type에서 필드만 override하면 directive가 따라가지 않음 
    - 라인 파싱이므로 당연한 결과라 template에는 inline으로 한줄로 작성합니다. 
    - 아래 예제 참고 (failed_example는 오류가 발생하는 케이스. passover_example 필드와 같이 사용하면 됨.)

# Directives 

- 현재 동작 체크된 Directives
  - @node, @fulltext, @cypher, @relationship, @timestamp, @unique, @declareRelationship, @settable, @filterable

##  interface Directives for type 

- interface에서 type에만 적용되야할 주석이 있다면 `# @~` 로 작성합니다.
- `@이름(내용)` 구조인 directive라면 제한적으로 멀티라인 가능합니다. (ex @cypher)

## interface Directives

- @declareRelationship 
  - `# @relationship` 으로 바로 선언해서 사용합니다.
    - @relationship을 선언을 강제하는건데 바로 @relationship을 injection하므로 사용하지 않습니다. 
    - 구현받는 타입에서 달라져야 하는경우 inline으로 작성해서 override 합니다. 

# Example
- 코드 외 설명은 ## 주석으로 추가. 

./template/sample.template.gql 
```graphql
interface BaseObject {
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
    totalItems:Int
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as totalItems
    # """, columnName: "totalItems")
}
interface SecondObject implements BaseObject {
    name: String!
    type: String!
    identity: Identity # @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    ## 이 필드는 아래에서 Override되는데 그러면 사이퍼 선언 위치때문에 오류발생합니다. 
    failed_example:Int
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as failed_example
    # """, columnName: "failed_example")
    ## 이런 경우 아래와 같이 선언해서 우회할수 있습니다. 
    passover_example:Int # @cypher(statement: """MATCH (this)-[:HAS_ITEM]->(items) RETURN count(items) as passover_example""", columnName: "passover_example")
    
}
type User implements SecondObject @node(labels: ["User", "$context.userId"]) {
    type: [String!]!
    social: Social @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    entertainment: Entertainment @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    lifestyle: Lifestyle @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    failed_example:Int!
    passover_example:Float # @cypher(statement: """MATCH (this)-[:HAS_ITEM]->(items) RETURN count(items) as passover_example""", columnName: "passover_example")
}
```

./schemas/sample.gql 
```graphql
interface BaseObject {
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
    totalItems:Int
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as totalItems
    # """, columnName: "totalItems")
}
interface SecondObject implements BaseObject {
    name: String!
    type: String!
    identity: Identity # @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    failed_example:Int
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as failed_example
    # """, columnName: "failed_example")
    passover_example:Int # @cypher(statement: """MATCH (this)-[:HAS_ITEM]->(items) RETURN count(items) as passover_example""", columnName: "passover_example")
    # from BaseObject
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
    totalItems:Int
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as totalItems
    # """, columnName: "totalItems")
}
type User implements SecondObject & BaseObject @node(labels: ["User", "$context.userId"]) {
    ## User type에 이미 있으므로 SecondObject 값은 가져오지 않습니다. 
    type: [String!]!  
    social: Social @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    entertainment: Entertainment @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    lifestyle: Lifestyle @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    failed_example:Int ## override라 위에 선언되는데 cypher는 하단에 선언되서 Validation fail.
    passover_example:Float @cypher(statement: """MATCH (this)-[:HAS_ITEM]->(items) RETURN count(items) as passover_example""", columnName: "passover_example")
    # from BaseObject
    id: String! @unique
    created: DateTime @timestamp(operations: [CREATE])
    updated: DateTime @timestamp(operations: [CREATE, UPDATE])
    totalItems:Int
    @cypher(statement: """  
    MATCH (this)-[:HAS_ITEM]->(items)
    RETURN count(items) as totalItems
    """, columnName: "totalItems")
    # from SecondObject
    name: String!
    type: String!
    identity: Identity @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    ## 파싱 규칙상 여기에 생성되는데 gql 지시자 위치 오류임. 
    @cypher(statement: """  
    MATCH (this)-[:HAS_ITEM]->(items)
    RETURN count(items) as failed_example
    """, columnName: "failed_example")
    
    # from BaseObject
    ## 재귀호출이라 SecondObject 내용을 injection 하는데 전부 위에 선언되있으므로 가져오지 않습니다.
}
```
