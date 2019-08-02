import pytest
from pytest_bdd import scenario, given, when, then

from scanapi.requests_builder import RequestsBuilder


@pytest.fixture(autouse=True)
def mock_get_request(mocker):
    return mocker.patch("scanapi.requests_builder.requests.get")


@pytest.fixture
def api_spec():
    return {"api": {"base_url": "", "requests": [{"name": "", "method": ""}]}}


@scenario(
    "call_requests.feature",
    "API spec with only base_url and one request with name and method",
)
def test_call_requests():
    pass


@given("base_url is correct", target_fixture="api_spec")
def base_url(api_spec):
    api_spec["api"]["base_url"] = "https://jsonplaceholder.typicode.com/todos"
    return api_spec


@given("HTTP method is GET", target_fixture="api_spec")
def http_method(api_spec):
    api_spec["api"]["requests"][0]["method"] = "get"
    return api_spec


@then("the request should be made")
def get_called(api_spec, mock_get_request):
    RequestsBuilder(api_spec).call_all()

    mock_get_request.assert_called_once_with(
        "https://jsonplaceholder.typicode.com/todos", headers={}, params={}
    )