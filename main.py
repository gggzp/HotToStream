import requests
from bs4 import BeautifulSoup
import streamlit as st

onedrive_shared_link = st.secrets['onedrive_shared_link']


def download_folder_from_onedrive(onedrive_shared_link):
    response = requests.get(onedrive_shared_link)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.find_all('div', class_='fileLink')
    
    files_content = {}
    for item in items:
        file_url = item.find('a')['href']
        file_name = file_url.split('/')[-1]
        print(f"Found file: {file_name}")  # Debug print
        
        file_response = requests.get(file_url)
        file_response.raise_for_status()
        
        files_content[file_name] = file_response.content
    
    return files_content
# 在Streamlit应用中使用
if st.button('从OneDrive下载文件'):
    files_content= download_folder_from_onedrive(onedrive_shared_link)
    st.write('已从OneDrive下载文件')
    st.session_state['files_content']= files_content
    # 检查是否下载了文件
    if st.session_state['files_content']:
        st.write(list(st.session_state['files_content'].keys()))
    else:
        st.error('没有找到文件或无法下载文件')
