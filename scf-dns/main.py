import base64
import socket

def base64url_decode(data):
    data = data.replace('-', '+').replace('_', '/')
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return base64.b64decode(data)

def send_udp_query(query_data, address='8.8.8.8', port=53, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(query_data, (address, port))
        response, _ = sock.recvfrom(512)
        return response
    except socket.timeout:
        return None
    finally:
        sock.close()

def main_handler(event, context):
    http_method = event.get('httpMethod', '').upper()
    headers = event.get('headers', {})
    response_headers = {'Content-Type': 'application/dns-message'}
    
    # 处理GET请求
    if http_method == 'GET':
        query_params = event.get('queryStringParameters', {})
        dns_param = query_params.get('dns')
        
        if not dns_param:
            return {
                'isBase64Encoded': False,
                'statusCode': 400,
                'headers': response_headers,
                'body': 'Missing "dns" query parameter'
            }
        
        try:
            dns_query_data = base64url_decode(dns_param)
        except Exception as e:
            return {
                'isBase64Encoded': False,
                'statusCode': 400,
                'headers': response_headers,
                'body': f'Invalid parameter: {str(e)}'
            }
    
    # 处理POST请求
    elif http_method == 'POST':
        content_type = headers.get('content-type', '').lower()
        if content_type != 'application/dns-message':
            return {
                'isBase64Encoded': False,
                'statusCode': 415,
                'headers': response_headers,
                'body': 'Unsupported media type'
            }
        
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        try:
            if is_base64:
                dns_query_data = base64.b64decode(body)
            else:  # 非base64请求体视为无效
                return {
                    'isBase64Encoded': False,
                    'statusCode': 400,
                    'headers': response_headers,
                    'body': 'Request body must be base64 encoded'
                }
        except Exception as e:
            return {
                'isBase64Encoded': False,
                'statusCode': 400,
                'headers': response_headers,
                'body': f'Invalid body: {str(e)}'
            }
    
    else:  # 不支持的其他方法
        return {
            'isBase64Encoded': False,
            'statusCode': 405,
            'headers': {'Allow': 'GET, POST'},
            'body': 'Method not allowed'
        }
    
    # 转发DNS查询并获取响应
    dns_response = send_udp_query(dns_query_data)
    if not dns_response:
        return {
            'isBase64Encoded': False,
            'statusCode': 504,
            'headers': response_headers,
            'body': 'Upstream DNS timeout'
        }
    
    # 返回封装响应
    return {
        'isBase64Encoded': True,
        'statusCode': 200,
        'headers': response_headers,
        'body': base64.b64encode(dns_response).decode()
    }
