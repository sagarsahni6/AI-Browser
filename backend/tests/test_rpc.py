from backend.app.browser.protocol import JsonRpcRequest, JsonRpcResponse, JsonRpcError

def test_json_rpc_serialization():
    req = JsonRpcRequest(id=1, method="browser.inspect", params={"tab_id": "tab-1"})
    serialized = req.model_dump_json()
    assert '"jsonrpc":"2.0"' in serialized
    assert '"method":"browser.inspect"' in serialized

    res = JsonRpcResponse(id=1, result={"title": "Test Page"})
    res_serialized = res.model_dump_json()
    assert '"jsonrpc":"2.0"' in res_serialized
    assert '"title":"Test Page"' in res_serialized

    err_res = JsonRpcResponse(id=2, error=JsonRpcError(code=-32601, message="Method not found"))
    err_serialized = err_res.model_dump_json()
    assert '-32601' in err_serialized
