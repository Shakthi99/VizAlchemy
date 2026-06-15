let
    Source = Sql.Database("sql-prod.company.com", "SalesDB"),
    Table = Source{[Schema="dbo", Item="Orders"]}[Data]
in
    Table