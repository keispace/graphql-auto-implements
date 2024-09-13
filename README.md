# graphql-auto-implements


./template 폴더의 모든 gql 읽어서 implements 구조대로 field 채워주는 코드. 


# Usage

- ./template 폴더 내에 ~.template.gql 로 파일을 작성합니다. 
- implements는 연결된 모든 interface를 작성합니다.(추후 정리 예정. )
- type Directives 는 동일하게 작성합니다.
- ./schemas 폴더로 export 됩니다.
- 폴더 구조 유지됩니다. 
- 주석, enum, union은 그대로 복사합니다. 
- 중복된 field는 하위 type 값이 유지됩니다.(implement override)


# Directives 

- 현재 동작 체크된 Directives
  - @node, @cypher, @relationship, @timestamp, @unique, @declareRelationship 

##  interface Directives for type 

- interface에서 type에만 적용되야할 주석이 있다면 `# @~` 로 작성합니다.
- `@이름(내용)` 구조인 directive라면 멀티라인 가능합니다. (ex @cypher)

## interface Directives

- @declareRelationship 
  - @relationship을 선언을 강제하는건데 바로 @relationship을 injection하므로 사용하지 않습니다. 
  - `# @relationship` 으로 바로 선언해서 사용합니다.

# Example
- 코드 외 설명은 ## 주석으로 추가. 

./template/sample.template.gql 
```graphql
interface BaseObject {
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as totalItems
    # """, columnName: "totalItems")
}
interface SecondObject implements BaseObject {
    name: String!
    type: String!
    identity: Identity # @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
}
type User implements BaseObject @node(labels: ["User", "$context.userId"]) {
    type: [String!]!
    social: Social @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    entertainment: Entertainment @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    lifestyle: Lifestyle @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
}
```

./schemas/sample.gql 
```graphql
interface BaseObject {
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
    # @cypher(statement: """  
    # MATCH (this)-[:HAS_ITEM]->(items)
    # RETURN count(items) as totalItems
    # """, columnName: "totalItems")
}
interface SecondObject implements BaseObject {
    name: String!
    type: String!
    identity: Identity # @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    # from BaseObject
    id: String! # @unique
    created: DateTime # @timestamp(operations: [CREATE])
    updated: DateTime # @timestamp(operations: [CREATE, UPDATE])
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
    # from BaseObject
    id: String! @unique
    created: DateTime @timestamp(operations: [CREATE])
    updated: DateTime @timestamp(operations: [CREATE, UPDATE])
    @cypher(statement: """  
    MATCH (this)-[:HAS_ITEM]->(items)
    RETURN count(items) as totalItems
    """, columnName: "totalItems")
    # from SecondObject
        name: String!
    type: String!
    identity: Identity @relationship(type: "HAS_DATA_CIRCLE", direction: OUT)
    # from BaseObject
    ## 재귀호출이라 SecondObject 내용을 injection 하는데 전부 위에 선언되있으므로 가져오지 않습니다.
}
```
