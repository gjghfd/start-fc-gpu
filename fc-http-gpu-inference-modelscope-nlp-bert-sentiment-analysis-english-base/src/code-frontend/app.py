from flask import Flask, render_template, request
import os
import sys
import traceback
import pymysql
import tablestore


# init flask
app = Flask(__name__, template_folder="./template")


# init ots
ots_endpoint = os.environ['OTS_ENDPOINT']
ots_ak_id = os.environ['OTS_AK_ID']
ots_ak_secret = os.environ['OTS_AK_SECRET']
ots_instance = os.environ['OTS_INSTANCE']
ots_table = "mall_comments_mock"
ots_client = tablestore.OTSClient(ots_endpoint, ots_ak_id, ots_ak_secret, ots_instance, logger_name = 'table_store.log')


@app.route('/initialize', methods=['POST'])
def initialize():
    # See FC docs for all the HTTP headers: https://www.alibabacloud.com/help/doc-detail/132044.htm#common-headers
    request_id = request.headers.get("x-fc-request-id", "")
    print("FC Initialize Start RequestId: " + request_id)

    # do your things
    # Use the following code to get temporary credentials
    # access_key_id = request.headers['x-fc-access-key-id']
    # access_key_secret = request.headers['x-fc-access-key-secret']
    # access_security_token = request.headers['x-fc-security-token']

    print("FC Initialize End RequestId: " + request_id)
    return "Function is initialized, request_id: " + request_id + "\n"


@app.route('/invoke', methods=['GET'])
def invoke():
    # See FC docs for all the HTTP headers: https://www.alibabacloud.com/help/doc-detail/132044.htm#common-headers
    request_id = request.headers.get("x-fc-request-id", "")
    print("FC Invoke Start RequestId: " + request_id)

    try:
        data = fetch_dataset()
        return render_template("rating.html", data = data)
    except Exception as e:
        exc_info = sys.exc_info()
        trace = traceback.format_tb(exc_info[2])
        errRet = {
            "message": str(e),
            "stack": trace
        }
        print(errRet)
        print("FC Invoke End RequestId: " + request_id)
        return errRet, 404, [("x-fc-status", "404")]


def fetch_dataset():
    inclusive_start_primary_key = [('product_id', tablestore.INF_MIN), ('user_id', tablestore.INF_MIN)]
    exclusive_end_primary_key = [('product_id', tablestore.INF_MAX), ('user_id', tablestore.INF_MAX)]
    columns_to_get = []
    limit = 1000
    try:
        consumed, next_start_primary_key, row_list, next_token = ots_client.get_range(
            ots_table, tablestore.Direction.FORWARD,
            inclusive_start_primary_key, exclusive_end_primary_key,
            columns_to_get, limit, max_version = 1)
        all_rows = []
        all_rows.extend(row_list)

        while next_start_primary_key is not None:
            inclusive_start_primary_key = next_start_primary_key
            consumed, next_start_primary_key, row_list, next_token = ots_client.get_range(
                ots_table, tablestore.Direction.FORWARD,
                inclusive_start_primary_key, exclusive_end_primary_key,
                columns_to_get, limit, max_version = 1)
            all_rows.extend(row_list)

        print('Total rows: ', len(all_rows))

        result = []
        for item in all_rows:
            comment_id = 0
            product_id = item.primary_key[0][1]
            user_id = item.primary_key[1][1]
            comment_content = item.attribute_columns[0][1]
            comment_rating_negative = item.attribute_columns[1][1]
            comment_rating_neutral = item.attribute_columns[2][1]
            comment_rating_positive = item.attribute_columns[3][1]
            result.append([comment_id, user_id, product_id, 0, comment_content, comment_rating_positive, comment_rating_neutral, comment_rating_negative])
        return result
    except tablestore.OTSClientError as e:
        print("get row failed, http_status:%d, error_message:%s" % (e.get_http_status(), e.get_error_message()))
    except tablestore.OTSServiceError as e:
        print("get row failed, http_status:%d, error_code:%s, error_message:%s, request_id:%s" % (e.get_http_status(), e.get_error_code(), e.get_error_message(), e.get_request_id()))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=9000)

