from decimal import Decimal
from unittest.mock import patch

import pytest

from baserow.contrib.builder.elements.exceptions import (
    ElementDoesNotExist,
    ElementNotInSamePage,
)
from baserow.contrib.builder.elements.models import Element
from baserow.contrib.builder.elements.registries import element_type_registry
from baserow.contrib.builder.elements.service import ElementService
from baserow.core.exceptions import PermissionException


def pytest_generate_tests(metafunc):
    if "element_type" in metafunc.fixturenames:
        metafunc.parametrize(
            "element_type",
            [pytest.param(e, id=e.type) for e in element_type_registry.get_all()],
        )


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_created")
def test_create_element(element_created_mock, data_fixture, element_type):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page, order="1.0000")
    element3 = data_fixture.create_builder_heading_element(page=page, order="2.0000")

    sample_params = element_type.get_sample_params()

    element = ElementService().create_element(
        user, element_type, page=page, **sample_params
    )

    last_element = Element.objects.last()

    # Check it's the last element
    assert last_element.id == element.id

    assert element_created_mock.called_with(element=element, user=user)


@pytest.mark.django_db
def test_create_element_before(data_fixture):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page, order="1.0000")
    element3 = data_fixture.create_builder_heading_element(page=page, order="2.0000")

    element_type = element_type_registry.get("heading")
    sample_params = element_type.get_sample_params()

    element2 = ElementService().create_element(
        user, element_type, page=page, before=element3, **sample_params
    )

    elements = Element.objects.all()
    assert elements[0].id == element1.id
    assert elements[1].id == element2.id
    assert elements[2].id == element3.id


@pytest.mark.django_db
def test_create_element_before_not_same_page(data_fixture):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page, order="1.0000")
    element3 = data_fixture.create_builder_heading_element(order="2.0000")

    element_type = element_type_registry.get("heading")
    sample_params = element_type.get_sample_params()

    with pytest.raises(ElementNotInSamePage):
        ElementService().create_element(
            user, element_type, page=page, before=element3, **sample_params
        )


@pytest.mark.django_db
def test_get_unique_orders_before_element_triggering_full_page_order_reset(
    data_fixture,
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element_1 = data_fixture.create_builder_heading_element(
        page=page, order="1.00000000000000000000"
    )
    element_2 = data_fixture.create_builder_heading_element(
        page=page, order="1.00000000000000001000"
    )
    element_3 = data_fixture.create_builder_heading_element(
        page=page, order="2.99999999999999999999"
    )
    element_4 = data_fixture.create_builder_heading_element(
        page=page, order="2.99999999999999999998"
    )

    element_type = element_type_registry.get("heading")
    sample_params = element_type.get_sample_params()

    element_created = ElementService().create_element(
        user, element_type, page=page, before=element_3, **sample_params
    )

    element_1.refresh_from_db()
    element_2.refresh_from_db()
    element_3.refresh_from_db()
    element_4.refresh_from_db()

    assert element_1.order == Decimal("1.00000000000000000000")
    assert element_2.order == Decimal("2.00000000000000000000")
    assert element_4.order == Decimal("3.00000000000000000000")
    assert element_3.order == Decimal("4.00000000000000000000")
    assert element_created.order == Decimal("3.50000000000000000000")


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_orders_recalculated")
def test_recalculate_full_order(element_orders_recalculated_mock, data_fixture):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    data_fixture.create_builder_heading_element(page=page, order="1.9000")
    data_fixture.create_builder_heading_element(page=page, order="3.4000")

    ElementService().recalculate_full_orders(user, page)

    assert element_orders_recalculated_mock.called_with(page=page, user=user)


@pytest.mark.django_db
def test_create_element_permission_denied(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)

    element_type = element_type_registry.get("heading")

    with stub_check_permissions(raise_permission_denied=True), pytest.raises(
        PermissionException
    ):
        ElementService().create_element(
            user, element_type, page=page, **element_type.get_sample_params()
        )


@pytest.mark.django_db
def test_get_element(data_fixture):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    assert ElementService().get_element(user, element.id).id == element.id


@pytest.mark.django_db
def test_get_element_does_not_exist(data_fixture):
    user = data_fixture.create_user()

    with pytest.raises(ElementDoesNotExist):
        assert ElementService().get_element(user, 0)


@pytest.mark.django_db
def test_get_element_permission_denied(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    with stub_check_permissions(raise_permission_denied=True), pytest.raises(
        PermissionException
    ):
        ElementService().get_element(user, element.id)


@pytest.mark.django_db
def test_get_elements(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page)
    element2 = data_fixture.create_builder_heading_element(page=page)
    element3 = data_fixture.create_builder_paragraph_element(page=page)

    assert [p.id for p in ElementService().get_elements(user, page)] == [
        element1.id,
        element2.id,
        element3.id,
    ]

    def exclude_element_1(
        actor,
        operation_name,
        queryset,
        workspace=None,
        context=None,
        allow_if_template=False,
    ):
        return queryset.exclude(id=element1.id)

    with stub_check_permissions() as stub:
        stub.filter_queryset = exclude_element_1

        assert [p.id for p in ElementService().get_elements(user, page)] == [
            element2.id,
            element3.id,
        ]


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_deleted")
def test_delete_element(element_deleted_mock, data_fixture):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    ElementService().delete_element(user, element)

    assert element_deleted_mock.called_with(element_id=element.id, user=user)


@pytest.mark.django_db(transaction=True)
def test_delete_element_permission_denied(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    with stub_check_permissions(raise_permission_denied=True), pytest.raises(
        PermissionException
    ):
        ElementService().delete_element(user, element)


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_updated")
def test_update_element(element_updated_mock, data_fixture):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    element_updated = ElementService().update_element(user, element, value="newValue")

    assert element_updated_mock.called_with(element=element_updated, user=user)


@pytest.mark.django_db(transaction=True)
def test_update_element_permission_denied(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    element = data_fixture.create_builder_heading_element(user=user)

    with stub_check_permissions(raise_permission_denied=True), pytest.raises(
        PermissionException
    ):
        ElementService().update_element(user, element, value="newValue")


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_updated")
def test_move_element(element_updated_mock, data_fixture):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page)
    element2 = data_fixture.create_builder_heading_element(page=page)
    element3 = data_fixture.create_builder_paragraph_element(page=page)

    element_moved = ElementService().move_element(user, element3, before=element2)

    assert element_updated_mock.called_with(element=element_moved, user=user)


@pytest.mark.django_db
def test_move_element_not_same_page(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    page2 = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page)
    element2 = data_fixture.create_builder_heading_element(page=page)
    element3 = data_fixture.create_builder_paragraph_element(page=page2)

    with pytest.raises(ElementNotInSamePage):
        ElementService().move_element(user, element3, before=element2)


@pytest.mark.django_db
def test_move_element_permission_denied(data_fixture, stub_check_permissions):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(page=page)
    element2 = data_fixture.create_builder_heading_element(page=page)
    element3 = data_fixture.create_builder_paragraph_element(page=page)

    with stub_check_permissions(raise_permission_denied=True), pytest.raises(
        PermissionException
    ):
        ElementService().move_element(user, element3, before=element2)


@pytest.mark.django_db
@patch("baserow.contrib.builder.elements.service.element_orders_recalculated")
def test_move_element_trigger_order_recalculed(
    element_orders_recalculated_mock, data_fixture
):
    user = data_fixture.create_user()
    page = data_fixture.create_builder_page(user=user)
    element1 = data_fixture.create_builder_heading_element(
        page=page, order="2.99999999999999999998"
    )
    element2 = data_fixture.create_builder_heading_element(
        page=page, order="2.99999999999999999999"
    )
    element3 = data_fixture.create_builder_heading_element(page=page, order="3.0000")

    ElementService().move_element(user, element3, before=element2)

    assert element_orders_recalculated_mock.called_with(page=page, user=user)
