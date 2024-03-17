DB_PROPERTY = {
    'users': {
        'user_id': {'dtype':'int', 'auto_increment':True},
        'username': {'dtype': 'str'},
        'password': {'dtype': 'str'},
        'permission': {'dtype': 'int'},
        'auth_method': {'dtype': 'str'},
    }
}

class Database:
    def __init__(self, db_properties):
        self.db_properties = db_properties
        self.data = {table: [] for table in db_properties}
        self.auto_increment_values = {table: {field: 0 for field, props in fields.items() if props.get('auto_increment', False)} for table, fields in db_properties.items()}

    def create(self, table, data):
        if table not in self.db_properties:
            raise ValueError(f"Table '{table}' does not exist.")
        new_record = {}
        for field, properties in self.db_properties[table].items():
            if properties.get('auto_increment', False):
                self.auto_increment_values[table][field] += 1
                new_record[field] = self.auto_increment_values[table][field]
            else:
                new_record[field] = data.get(field)
        self.data[table].append(new_record)
        return new_record

    def read(self, table, criteria):
        if table not in self.db_properties:
            raise ValueError(f"Table '{table}' does not exist.")
        records = []
        for record in self.data[table]:
            if all(record.get(field) == value for field, value in criteria.items()):
                records.append(record)
        return records

    def update(self, table, criteria, new_data):
        if table not in self.db_properties:
            raise ValueError(f"Table '{table}' does not exist.")
        updated_count = 0
        for record in self.data[table]:
            if all(record.get(field) == value for field, value in criteria.items()):
                for key, value in new_data.items():
                    if key in self.db_properties[table]:
                        record[key] = value
                updated_count += 1
        return updated_count

    def delete(self, table, criteria):
        if table not in self.db_properties:
            raise ValueError(f"Table '{table}' does not exist.")
        to_delete = []
        for i, record in enumerate(self.data[table]):
            if all(record.get(field) == value for field, value in criteria.items()):
                to_delete.append(i)
        for i in reversed(to_delete):  # Delete in reverse order to avoid index issues
            del self.data[table][i]
        return len(to_delete)
