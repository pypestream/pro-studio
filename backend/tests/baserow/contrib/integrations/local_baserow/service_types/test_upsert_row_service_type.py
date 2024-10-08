from io import BytesIO
from unittest.mock import Mock

import pytest
from rest_framework.exceptions import ValidationError

from baserow.contrib.builder.data_sources.builder_dispatch_context import (
    BuilderDispatchContext,
)
from baserow.contrib.builder.data_sources.service import DataSourceService
from baserow.contrib.builder.workflow_actions.models import EventTypes
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.database.table.handler import TableHandler
from baserow.contrib.integrations.local_baserow.models import (
    LocalBaserowGetRow,
    LocalBaserowUpsertRow,
)
from baserow.contrib.integrations.local_baserow.service_types import (
    LocalBaserowUpsertRowServiceType,
)
from baserow.core.handler import CoreHandler
from baserow.core.registries import ImportExportConfig
from baserow.core.services.exceptions import ServiceImproperlyConfigured


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_without_row_id(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Ingredient", "text", {}),
        ],
    )
    ingredient = table.field_set.get(name="Ingredient")

    service = data_fixture.create_local_baserow_upsert_row_service(
        integration=integration,
        table=table,
    )
    service_type = service.get_type()
    service.field_mappings.create(field=ingredient, value='get("page_parameter.id")')

    fake_request = Mock()
    fake_request.data = {"page_parameter": {"id": 2}}

    dispatch_context = BuilderDispatchContext(fake_request, page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    assert getattr(dispatch_data["data"], ingredient.db_column) == str(
        fake_request.data["page_parameter"]["id"]
    )


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_with_row_id(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Cost", "number", {}),
        ],
    )
    cost = table.field_set.get(name="Cost")
    row = RowHandler().create_row(
        user=user,
        table=table,
        values={f"field_{cost.id}": 5},
    )

    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        row_id=f"'{row.id}'",
        integration=integration,
    )
    service_type = service.get_type()
    service.field_mappings.create(field=cost, value='get("page_parameter.id")')

    fake_request = Mock()
    fake_request.data = {"page_parameter": {"id": 10}}

    dispatch_context = BuilderDispatchContext(fake_request, page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    assert (
        getattr(dispatch_data["data"], cost.db_column)
        == fake_request.data["page_parameter"]["id"]
    )

    row.refresh_from_db()
    assert getattr(row, cost.db_column) == fake_request.data["page_parameter"]["id"]

    # Same test but the page parameter is a string instead.
    fake_request.data = {"page_parameter": {"id": "10"}}
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    assert getattr(dispatch_data["data"], cost.db_column) == int(
        fake_request.data["page_parameter"]["id"]
    )

    row.refresh_from_db()
    assert getattr(row, cost.db_column) == int(
        fake_request.data["page_parameter"]["id"]
    )


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_disabled_field_mapping_fields(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Name", "text", {}),
            ("Last name", "text", {}),
            ("Location", "text", {}),
        ],
    )

    name_field = table.field_set.get(name="Name")
    last_name_field = table.field_set.get(name="Last name")
    location_field = table.field_set.get(name="Location")

    row = RowHandler().create_row(
        user=user,
        table=table,
        values={
            name_field.id: "Peter",
            last_name_field.id: "Evans",
            location_field.id: "Cornwall",
        },
    )

    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        row_id=f"'{row.id}'",
        integration=integration,
    )
    service_type = service.get_type()
    service.field_mappings.create(field=name_field, value="'Jeff'", enabled=True)
    service.field_mappings.create(field=last_name_field, value="", enabled=False)
    service.field_mappings.create(field=location_field, value="", enabled=False)

    fake_request = Mock()
    dispatch_context = BuilderDispatchContext(fake_request, page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    service_type.dispatch_data(service, dispatch_values, dispatch_context)

    row.refresh_from_db()
    assert getattr(row, name_field.db_column) == "Jeff"
    assert getattr(row, last_name_field.db_column) == "Evans"
    assert getattr(row, location_field.db_column) == "Cornwall"


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_with_multiple_formulas(
    data_fixture,
):
    user = data_fixture.create_user()
    builder = data_fixture.create_builder_application(user=user)
    page = data_fixture.create_builder_page(builder=builder)
    integration = data_fixture.create_local_baserow_integration(
        application=builder, user=user, authorized_user=user
    )
    database = data_fixture.create_database_application(workspace=builder.workspace)
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Cost", "number", {}),
            ("Name", "text", {}),
        ],
    )
    cost = table.field_set.get(name="Cost")
    name = table.field_set.get(name="Name")
    row = RowHandler().create_row(
        user=user,
        table=table,
        values={cost.db_column: 5, name.db_column: "test"},
    )

    data_source = data_fixture.create_builder_local_baserow_get_row_data_source(
        page=page, table=table, integration=integration
    )

    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        row_id=f'get("data_source.{data_source.id}.id")',
        integration=integration,
    )
    service_type = service.get_type()
    service.field_mappings.create(
        field=cost, value=f'get("data_source.{data_source.id}.{cost.db_column}")'
    )
    service.field_mappings.create(
        field=name, value=f'get("data_source.{data_source.id}.{name.db_column}")'
    )

    fake_request = Mock()
    fake_request.data = {"page_parameter": {"id": 10}}

    dispatch_context = BuilderDispatchContext(fake_request, page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    row.refresh_from_db()
    assert getattr(row, cost.db_column) == 5


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_with_unknown_row_id(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    table = data_fixture.create_database_table(user=user)
    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        row_id="'9999999999999'",
        integration=integration,
    )
    service_type = service.get_type()
    dispatch_context = BuilderDispatchContext(Mock(), page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    with pytest.raises(ServiceImproperlyConfigured) as exc:
        service_type.dispatch_data(service, dispatch_values, dispatch_context)
    assert exc.value.args[0] == "The row with id 9999999999999 does not exist."


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_with_read_only_table_field(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("UUID", "uuid", {}),
            ("Ingredient", "text", {}),
        ],
    )
    uuid = table.field_set.get(name="UUID")
    ingredient = table.field_set.get(name="Ingredient")

    service = data_fixture.create_local_baserow_upsert_row_service(
        integration=integration,
        table=table,
    )
    service_type = service.get_type()
    service.field_mappings.create(
        field=uuid, value="'b52d8848-f2c2-4495-b8ef-94e1b4f3c49f'"
    )
    service.field_mappings.create(field=ingredient, value="'Potato'")

    dispatch_context = BuilderDispatchContext(Mock(), page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    assert (
        getattr(dispatch_data["data"], uuid.db_column)
        != "b52d8848-f2c2-4495-b8ef-94e1b4f3c49f"
    )
    assert getattr(dispatch_data["data"], ingredient.db_column) == "Potato"


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_transform(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Ingredient", "text", {}),
        ],
    )
    ingredient = table.field_set.get(name="Ingredient")

    service = data_fixture.create_local_baserow_upsert_row_service(
        integration=integration,
        table=table,
    )
    service_type = service.get_type()
    service.field_mappings.create(field=ingredient, value='get("page_parameter.id")')

    fake_request = Mock()
    fake_request.data = {"page_parameter": {"id": 2}}

    dispatch_context = BuilderDispatchContext(fake_request, page)
    dispatch_values = service_type.resolve_service_formulas(service, dispatch_context)
    dispatch_data = service_type.dispatch_data(
        service, dispatch_values, dispatch_context
    )

    serialized_row = service_type.dispatch_transform(dispatch_data)
    assert dict(serialized_row) == {
        "id": dispatch_data["data"].id,
        "order": "1.00000000000000000000",
        ingredient.db_column: str(fake_request.data["page_parameter"]["id"]),
    }


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_dispatch_data_incompatible_value(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Active", "boolean", {}),
        ],
    )
    boolean_field = table.field_set.get()
    single_field = FieldHandler().create_field(
        user=user,
        table=table,
        name="Single Select",
        type_name="single_select",
        select_options=[
            {"value": "Option 1", "color": "blue"},
        ],
    )
    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        integration=integration,
    )
    service_type = service.get_type()
    dispatch_context = BuilderDispatchContext(Mock(), page)

    field_mapping = service.field_mappings.create(field=boolean_field, value="'Horse'")
    with pytest.raises(ServiceImproperlyConfigured) as exc:
        service_type.dispatch_data(
            service, {"table": table, field_mapping.id: "Horse"}, dispatch_context
        )

    service.field_mappings.all().delete()

    field_mapping = service.field_mappings.create(
        field=single_field, value="'99999999999'"
    )
    with pytest.raises(ServiceImproperlyConfigured) as exc:
        service_type.dispatch_data(
            service, {"table": table, field_mapping.id: "99999999999"}, dispatch_context
        )

    assert exc.value.args[0] == (
        "The result value of the formula is not valid for the "
        f"field `{single_field.name} ({single_field.db_column})`: "
        "The provided select option value '99999999999' is not a valid select option."
    )


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_resolve_service_formulas(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder, user=user
    )
    database = data_fixture.create_database_application(
        workspace=page.builder.workspace
    )
    table = TableHandler().create_table_and_fields(
        user=user,
        database=database,
        name=data_fixture.fake.name(),
        fields=[
            ("Name", "text", {}),
        ],
    )
    service = data_fixture.create_local_baserow_upsert_row_service(
        table=table,
        integration=integration,
    )
    service_type = service.get_type()

    dispatch_context = BuilderDispatchContext(Mock(), page)

    # We're creating a row.
    assert service.row_id == ""
    assert service_type.resolve_service_formulas(service, dispatch_context) == {
        "table": table,
    }

    # We're updating a row, but the ID isn't an integer
    service.row_id = "'horse'"
    with pytest.raises(ServiceImproperlyConfigured) as exc:
        service_type.resolve_service_formulas(service, dispatch_context)

    assert exc.value.args[0] == (
        "The result of the `row_id` formula must "
        "be an integer or convertible to an integer."
    )

    # We're updating a row, but the ID formula can't be resolved
    service.row_id = "'horse"
    with pytest.raises(ServiceImproperlyConfigured) as exc:
        service_type.resolve_service_formulas(service, dispatch_context)

    assert exc.value.args[0].startswith("The `row_id` formula can't be resolved")


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_prepare_values(data_fixture):
    user = data_fixture.create_user()
    with pytest.raises(ValidationError) as exc:
        LocalBaserowUpsertRowServiceType().prepare_values(
            {"table_id": 9999999999999999}, user
        )
    assert exc.value.args[0] == f"The table with ID 9999999999999999 does not exist."
    with pytest.raises(ValidationError) as exc:
        LocalBaserowUpsertRowServiceType().prepare_values(
            {"integration_id": 9999999999999999}, user
        )
    assert (
        exc.value.args[0] == f"The integration with ID 9999999999999999 does not exist."
    )


@pytest.mark.django_db(transaction=True)
def test_export_import_local_baserow_upsert_row_service(
    data_fixture,
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    builder = data_fixture.create_builder_application(workspace=workspace, order=2)
    page = data_fixture.create_builder_page(builder=builder)
    element = data_fixture.create_builder_button_element(page=page)
    database = data_fixture.create_database_application(workspace=workspace, order=1)
    table = data_fixture.create_database_table(database=database)
    field = data_fixture.create_text_field(table=table)
    integration = data_fixture.create_local_baserow_integration(application=builder)

    get_row_service = LocalBaserowGetRow.objects.create(integration=integration)
    data_source = DataSourceService().create_data_source(
        user, service_type=get_row_service.get_type(), page=page
    )
    upsert_row_service = data_fixture.create_local_baserow_upsert_row_service(
        integration=integration,
        table=table,
        row_id=f"get('data_source.{data_source.id}.{field.db_column}')",
    )
    upsert_row_service.field_mappings.create(
        field=field, value=f"get('data_source.{data_source.id}.{field.db_column}')"
    )

    data_fixture.create_local_baserow_create_row_workflow_action(
        page=page, element=element, event=EventTypes.CLICK, service=upsert_row_service
    )

    config = ImportExportConfig(include_permission_data=False)
    exported_applications = CoreHandler().export_workspace_applications(
        workspace, BytesIO(), config
    )

    imported_workspace = data_fixture.create_workspace(user=user)
    imported_applications, id_mapping = CoreHandler().import_applications_to_workspace(
        imported_workspace, exported_applications, BytesIO(), config, None
    )

    imported_database, imported_builder = imported_applications
    imported_table = imported_database.table_set.get()
    imported_field = imported_table.field_set.get()

    imported_page = imported_builder.page_set.get()
    imported_data_source = imported_page.datasource_set.get()
    imported_integration = imported_builder.integrations.get()
    imported_upsert_row_service = LocalBaserowUpsertRow.objects.get(
        integration=imported_integration
    )
    imported_field_mapping = imported_upsert_row_service.field_mappings.get()

    assert imported_field_mapping.field == imported_field
    assert (
        imported_field_mapping.value
        == f"get('data_source.{imported_data_source.id}.{imported_field.db_column}')"
    )
    assert (
        imported_upsert_row_service.row_id
        == f"get('data_source.{imported_data_source.id}.{imported_field.db_column}')"
    )


@pytest.mark.django_db()
def test_local_baserow_upsert_row_service_after_update(data_fixture):
    user, token = data_fixture.create_user_and_token()
    page = data_fixture.create_builder_page(user=user)
    integration = data_fixture.create_local_baserow_integration(
        application=page.builder
    )
    table = data_fixture.create_database_table()
    service = data_fixture.create_local_baserow_upsert_row_service(
        integration=integration,
        table=table,
    )
    field = data_fixture.create_text_field(table=table)
    LocalBaserowUpsertRowServiceType().after_update(
        service,
        {
            "table_id": table.id,
            "integration_id": integration.id,
            "field_mappings": [
                {"field_id": field.id, "value": "'Horse'", "enabled": True}
            ],
        },
        {},
    )
    assert service.field_mappings.count() == 1

    with pytest.raises(ValidationError) as exc:
        LocalBaserowUpsertRowServiceType().after_update(
            service,
            {
                "table_id": table.id,
                "field_mappings": [{"value": "'Bread'", "enabled": True}],
            },
            {},
        )
    assert exc.value.args[0] == "A field mapping must have a `field_id`."

    # Changing the table results in the `field_mapping` getting reset.
    table2 = data_fixture.create_database_table()
    service.table = table2
    service.save()

    with pytest.raises(ValidationError) as exc:
        LocalBaserowUpsertRowServiceType().after_update(
            service,
            {
                "field_mappings": [
                    {"field_id": field.id, "value": "'Pony'", "enabled": True}
                ],
            },
            {"table": (table, table2)},
        )
    assert exc.value.args[0] == f"The field with id {field.id} does not exist."
    service.refresh_from_db()
    assert service.table_id == table2.id
    assert service.field_mappings.count() == 0


@pytest.mark.django_db
def test_local_baserow_upsert_row_service_type_import_path(data_fixture):
    imported_upsert_row_service_type = LocalBaserowUpsertRowServiceType()

    assert imported_upsert_row_service_type.import_path(["id"], {}) == ["id"]
    assert imported_upsert_row_service_type.import_path(["field_1"], {}) == ["field_1"]
    assert imported_upsert_row_service_type.import_path(
        ["field_1"], {"database_fields": {1: 2}}
    ) == ["field_2"]
