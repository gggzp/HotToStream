import requests
import streamlit as st

# 从 Streamlit secrets 获取 OneDrive 共享链接
onedrive_shared_link = st.secrets['onedrive_shared_link']
st.write(onedrive_shared_link)

# 文件名已经知道，直接使用
file_name = 'RTGCrbf_model.joblib'

# 在 Streamlit 应用中使用
if st.button('从OneDrive下载文件'):
    # 发送 GET 请求获取文件内容
    response = requests.get(onedrive_shared_link)
    response.raise_for_status()  # 确保请求成功

    # 存储文件内容
    file_content = response.content

    # 显示文件大小
    file_size = len(file_content)
    st.write(f"文件名: {file_name}")
    st.write(f"文件大小: {file_size} bytes")

    # 如果需要，可以将文件内容保存到本地
    # with open(file_name, 'wb') as f:
    #     f.write(file_content)

    # 注意：由于文件可能不是文本格式，我们这里不尝试显示文件内容
    # 如果文件是文本格式，可以尝试以下代码显示内容
    # if file_name.endswith('.txt'):
    #     st.text(file_content.decode('utf-8'))
