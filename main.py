from scipy.interpolate import Rbf
import os
from joblib import dump, load
import pandas as pd
import numpy as np
from CoolProp.CoolProp import PropsSI
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Arrow
from cryptography.fernet import Fernet

key=st.secrets["key"]
cipher_suite = Fernet(key)

cipher_suite = Fernet(key)

def decrypt_data(encrypted_data, cipher_suite):
    try:
        # 解密数据
        decrypted_data = cipher_suite.decrypt(encrypted_data)
        return decrypted_data
    except Exception as e:
        print(f"解密时发生错误: {e}")
        return None

def load_and_decrypt_model(model_filename):
    # 加密模型文件路径
    encrypted_model_path = os.path.join('static', model_filename)
    st.write(encrypted_model_path)
    # 读取加密的模型文件内容
    with open(encrypted_model_path, 'rb') as file:
        encrypted_model_data = file.read()
    
    # 解密模型数据
    decrypted_model_data = decrypt_data(encrypted_model_data, cipher_suite)
    
    if decrypted_model_data is not None:
        # 使用 io.BytesIO 来模拟文件对象
        model_file = io.BytesIO(decrypted_model_data)
        
        # 从解密的数据加载模型
        model = load(model_file)
        return model
    else:
        return None

def main():
    st.title('余热产蒸汽系统')
    if st.button('开始计算'):
        encrypted_model_filename = "LockRTGCrbf_model.joblib"
        # 加载并解密模型
        joblib_model = load_and_decrypt_model(encrypted_model_filename)
        st.write(joblib_model)
        st.write('计算完成')


if __name__ == '__main__':
    main()
