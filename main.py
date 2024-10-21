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
import io


key=st.secrets["key"]
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


def get_saturated_vapor_pressure(temperature):#查询蒸汽压力
    # 参数：'P'表示压力，'T'表示温度，'Q'表示质量分数（0表示液相，1表示气相），'Water'表示水
    pressure = PropsSI('P', 'T', temperature + 273.15, 'Q', 1, 'Water') / 1e6  # 将压力从帕斯卡（Pa）转换为兆帕（MPa）
    return pressure

def get_saturated_vapor_enthalpy(temperature):#饱和蒸汽与饱和水焓差
    enthalpyStrem = PropsSI('H', 'T', temperature + 273.15, 'Q', 1, 'Water') / 1000  # 将焓值从焦耳每千克（J/kg）转换为千焦耳每千克（kJ/kg）
    enthalpyWater = PropsSI('H', 'T', temperature + 273.15, 'Q', 0, 'Water') / 1000  # 将焓值从焦耳每千克（J/kg）转换为千焦耳每千克（kJ/kg）
    enthalpy=enthalpyStrem-enthalpyWater
    return enthalpy

def get_saturated_vapor_specific_volume(temperature):#饱和蒸汽比体积立方米每千克（m³/kg）
    # 参数：'V'表示比体积，'T'表示温度，'Q'表示质量分数（0表示液相，1表示气相），'Water'表示水
    specific_volume = PropsSI('V', 'T', temperature + 273.15, 'Q', 1, 'Water')  # 返回值的单位是立方米每千克（m^3/kg）
    return specific_volume

def get_saturated_vapor_density(temperature):
    # 参数：'D'表示密度，'T'表示温度，'Q'表示质量分数（0表示液相，1表示气相），'Water'表示水
    density = PropsSI('D', 'T', temperature + 273.15, 'Q', 1, 'Water')  # 返回值的单位是千克每立方米（kg/m^3）
    return density


def GetValue(input_variables):
    HeatSourceType=input_variables['HeatSourceType']
    TG1=input_variables['TG1']
    TG2=input_variables['TG2']
    Tout1=input_variables['Tout1']
    Tout2=input_variables['Tout2']
    HeatSourceFlow=input_variables['HeatSourceFlow']
    AnnualOperatingHours=input_variables['AnnualOperatingHours']
    ElectricityUnitPrice=input_variables['ElectricityUnitPrice']
    SteamUnitPrice=input_variables['SteamUnitPrice']
    CoolingWaterUnitPrice=input_variables['CoolingWaterUnitPrice']
    TW1=input_variables['TW1']
    TW2=input_variables['TW2']
    Timddle=input_variables['Timddle']
    return HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2,Tmiddle

def AbsorptionHeatPump(HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2):#吸收式热泵COP
    model=1
    if TG2<=65:
        model=0
        Errordata="热源温度低于65度，无法使用二类热泵"
    elif Tout2>165:
        model=0
        Errordata="产出热温度太高，无法使用二类热泵。尝试降低蒸汽产出温度"
    else:
        TG12=(TG1+TG2)/2
        dTG=Tout2-TG12
        if TG2>=70:
            if dTG<=40:
                COP=0.48
            elif dTG<=80:
                COP=0.32
            else:
                model=0
                Errordata="产出热温度太高，无法使用二类热泵。尝试提高热源入口温度、出口温度或降低产出热温度"
        else:
            if dTG<=80:
                COP=0.32
            else:
                model=0
                COP=0
                Errordata="产出热温度太高，无法使用二类热泵。尝试提高热源入口温度、出口温度或降低产出热温度"                

        if COP == 0.32 and Tout2<(TG2-TG2/3): #二级升温
            model=0
            Errordata="产出热温度太高，无法使用二类热泵。尝试提高热源出口温度或降低产出热温度"

        if HeatSourceType=="蒸汽":
            WasteHeat=get_saturated_vapor_enthalpy(TG1)*HeatSourceFlow*1000/3600 #热源热量，单位kW
        elif HeatSourceType=="热水":
            WasteHeat=(TG1-TG2)*HeatSourceFlow/10/0.086 #热源热量，单位kW
        HeatGeneration = WasteHeat*COP #制热量kW
        StreamFlow = HeatGeneration/get_saturated_vapor_enthalpy(Tout2) /1000*3600 #流量单位t/h
        CoolingWaterGeneration = WasteHeat-HeatGeneration #冷却水热量kW
        CoolingWaterFlow=CoolingWaterGeneration*0.086*10/(TW2-TW1)
        OperatingCost=CoolingWaterFlow*CoolingWaterUnitPrice*AnnualOperatingHours/10000*0.02 #耗水成本  万元 补水率2%
        SteamCost=StreamFlow*SteamUnitPrice*AnnualOperatingHours/10000 #产蒸汽收益 万元
        NetIncome=(SteamCost-OperatingCost)  #净收益
        NetIncomePerStream= NetIncome/StreamFlow #净收益/流量单位t/h  每吨蒸汽收益 万元/吨
        if COP==0.48:
            if StreamFlow<0.55:
                model=0
                Errordata="产出蒸汽流量过低，二类热泵无对应小机器，请尝试增加热源热量"
            #elif StreamFlow>33:
                #model=0
                #Errordata="产出蒸汽流量过高，二类热泵无对应大机器，请尝试增加台数"                
        elif COP==0.32:
            if StreamFlow<0.35:
                model=0
                Errordata="产出蒸汽流量过低，二类热泵无对应小机器，请尝试增加热源热量"
            #elif StreamFlow>15:
                #model=0
                #Errordata="产出蒸汽流量过高，二类热泵无对应大机器，请尝试增加台数"

    if model == 0:
        results = {
            'model':model,
            'Errordata':Errordata,
        }
    else:
        results = {
            'model':model,
            'COP': COP,
            '制热量': HeatGeneration,
            '蒸汽流量': StreamFlow,
            '冷却水流量': CoolingWaterFlow,
            '冷却水成本': OperatingCost,
            '产蒸汽收益': SteamCost,
            '净收益': NetIncome,
            '每吨蒸汽收益': NetIncomePerStream
        }
    return results

def CentrifugalHeatPump (HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2):#离心热泵COP
    model=1
    if TG2>=90:
        model=0
        Errordata="余热出口温度太高，无法使用离心热泵。尝试降低余热出口温度"
    elif TG1>95:
        model=0
        Errordata="余热入口温度太高，无法使用离心热泵。尝试降低余热入口温度"
    elif Tout2>=125:
        model=0
        Errordata="蒸汽出口温度太高，无法使用离心热泵。尝试降低蒸汽出口温度"
    elif Tout2<=80:
        model=0
        Errordata="蒸汽出口温度太低，无法使用离心热泵。尝试提高蒸汽出口温度"
    elif Tout2-TG2 >=55 and TG2<=50:
        model=0
        Errordata="压比太高，无法使用离心热泵。尝试提高余热出口温度或降低余热产出温度"
    elif Tout2-TG2 >60:
        model=0
        Errordata="压比太高，无法使用离心热泵。尝试提高余热出口温度或降低余热产出温度"
    elif Tout2-TG2 < 25:
        model=0
        Errordata="压比太低，无法使用离心热泵。尝试降低余热出口温度或提高余热产出温度"
    if model == 1:
        # 加密模型文件名
        encrypted_model_filename = "LockRTGCrbf_model.joblib"
        # 加载并解密模型
        joblib_model = load_and_decrypt_model(encrypted_model_filename)
        COP = joblib_model(TG2,Tout2)
        WasteHeat=(TG1-TG2)*HeatSourceFlow/10/0.086 #热源热量，单位kW
        Elect=WasteHeat/(COP-1) #耗电量
        HeatGeneration=Elect+WasteHeat #制热量kW
        StreamFlow = HeatGeneration/get_saturated_vapor_enthalpy(Tout2) /1000*3600 #流量单位t/h
        OperatingCost=Elect*ElectricityUnitPrice*AnnualOperatingHours/10000 #耗电成本 万元/年
        SteamCost=StreamFlow*SteamUnitPrice*AnnualOperatingHours/10000 #产蒸汽收益 万元/年
        NetIncome=(SteamCost-OperatingCost)  #净收益
        NetIncomePerStream= NetIncome/StreamFlow #净收益/流量单位t/h  每吨蒸汽收益

        results = {
            'model':model,
            'COP': COP,
            '制热量': HeatGeneration,
            '蒸汽流量': StreamFlow,
            '耗电量': Elect,
            '耗电成本': OperatingCost,
            '产蒸汽收益': SteamCost,
            '净收益': NetIncome,
            '每吨蒸汽收益': NetIncomePerStream
        }
    else:
        results={
            'model':model,
            'Errordata':Errordata
        }
    return results

def SteamCompressor (HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2):#蒸汽压缩机单位蒸汽能耗
    model=1
    PressureTout2 = PropsSI('P', 'T', Tout2 + 273.15, 'Q', 1, 'Water') / 1e6
    PressureTG1 = PropsSI('P', 'T', TG1 + 273.15, 'Q', 1, 'Water') / 1e6
    CompressionRatio = PressureTout2/PressureTG1
    if PressureTout2>1.6:
        model=0
        Errordata="出口蒸汽压力过高，无法使用蒸汽压缩机，尝试降低出口蒸汽温度"
    else: 
        if CompressionRatio<=2:
            StageNumber=1
            encrypted_model_filename = "Lock压缩机1rbf_model.joblib"
            # 加载并解密模型
            joblib_model = load_and_decrypt_model(encrypted_model_filename)
            Ratio=1.03
        elif CompressionRatio<=4:
            StageNumber=2
            encrypted_model_filename = "Lock压缩机2rbf_model.joblib"
            # 加载并解密模型
            joblib_model = load_and_decrypt_model(encrypted_model_filename)
            Ratio=1.0392
        elif CompressionRatio<=8:
            StageNumber=3
            encrypted_model_filename = "Lock压缩机3rbf_model.joblib"
            # 加载并解密模型
            joblib_model = load_and_decrypt_model(encrypted_model_filename)
            Ratio=1.0583
        elif CompressionRatio<=16:
            StageNumber=4
            encrypted_model_filename = "Lock压缩机4rbf_model.joblib"
            # 加载并解密模型
            joblib_model = load_and_decrypt_model(encrypted_model_filename)
            Ratio=1.0769
        else:
            StageNumber=0
            model=0
            Errordata="压比过大，无法使用蒸汽压缩机，尝试降低出口蒸汽温度"
        #还需要做容量判断
    if model==1:
        StreamFlow = HeatSourceFlow*Ratio #单位 t/h
        StreamFlow_V=StreamFlow*1000/60/get_saturated_vapor_density(Tout2) #单位m3/min
        if StreamFlow_V<50:
            model=0
            Errordata="蒸汽流量过小，无法使用蒸汽压缩机，尝试增加蒸汽流量或降低蒸汽出口温度"
        else:
            COP = joblib_model(TG1,Tout2) #出口一kg蒸汽的耗电量 单位kWh/t
            Elect = StreamFlow*COP #电量单位 kW
            OperatingCost=Elect*ElectricityUnitPrice*AnnualOperatingHours/10000 #耗电成本 万元/年
            SteamCost=StreamFlow*SteamUnitPrice*AnnualOperatingHours/10000 #产蒸汽收益 万元/年
            NetIncome=(SteamCost-OperatingCost)  #净收益
            NetIncomePerStream= NetIncome/StreamFlow #净收益/流量单位t/h  每吨蒸汽收益
    if model==1:
        results = {
                'model': model,
                '级数': StageNumber,
                'COP': COP,
                '蒸汽流量': StreamFlow,
                '耗电量': Elect,
                '耗电成本': OperatingCost,
                '产蒸汽收益': SteamCost,
                '净收益': NetIncome,    
                '每吨蒸汽收益': NetIncomePerStream
            }
    else:
        results = {
            'model': model,
            'Errordata': Errordata
        }
    return results

def FlashEvaporation (HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2):#闪蒸
    model=1
    if HeatSourceType=="热水":
        WasteHeat=(TG1-TG2)*HeatSourceFlow/10/0.086 #热源热量，单位kW
        StreamFlow=WasteHeat/(get_saturated_vapor_enthalpy(TG2)*1000/3600) *0.9 #产蒸汽流量，单位t/h  其中0.9为系数90%
        Elect=HeatSourceFlow*28*1.15/0.82/367 #耗电量 单位kW
        PowerList=[0.4,0.75,1.5,2.2,3.7,5.5,7.5,11,15,18.5,22,30,37,45,55,75,90,110,132,160,185,200]
        for power in PowerList:
            if power >= Elect:
                Elect = power
                break
        OperatingCost=Elect*ElectricityUnitPrice*AnnualOperatingHours/10000 #耗电成本
        results= {
                'model':model,
                '蒸汽流量': StreamFlow,
                '蒸汽温度':TG2,
                '耗电量': Elect,
                '耗电成本': OperatingCost
        }
    else:
        model=0
        Errordata='蒸汽不适用'
        results={
            'model':model,
            'Errordata':Errordata
        }
    return results

def create_Abs_flowchart(TG1,TG2,Tout1,Tout2,TW1,TW2,ax): #单独吸收式热泵流程图

    Abs = FancyBboxPatch((0.4, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(Abs)

    ax.text(0.3, 0.85, '余热出口：'+str(TG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.3, 0.55, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
    # 可变文字部分，根据用户输入来显示
    ax.text(0.5, 0.7, '吸收式热泵', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.7, 0.55, '补水：'+str(Tout1)+'℃', ha='center', va='center', fontsize=8)   
    ax.text(0.5, 0.3, '冷却水温度：'+str(TW1)+'-'+str(TW2)+'℃', ha='center', va='center', fontsize=8)

    arrowTG2 = Arrow(0.4, 0.8, -0.2, 0, width=0.05, color='#00CED1')
    arrowTG1 = Arrow(0.2, 0.6, 0.2, 0, width=0.05, color='#00CED1')
    arrowTout2 = Arrow(0.6, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTout1 = Arrow(0.8, 0.6, -0.2, 0, width=0.05, color='#FF0000')    
    arrowTW1 = Arrow(0.45, 0.35, 0, 0.15, width=0.05, color='#3CB371')
    arrowTW2 = Arrow(0.55, 0.5, 0, -0.15, width=0.05, color='#3CB371')

    # 将箭头添加到图表上
    ax.add_patch(arrowTG2)
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowTout1)
    ax.add_patch(arrowTW1)
    ax.add_patch(arrowTW2)

    # 设置图表的显示范围和关闭坐标轴
    # 'set_xlim' 和 'set_ylim' 设置x轴和y轴的显示范围
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')

def create_SteamCompressor_flowchart(TG1,TG2,Tout2,StCompElect,ax): #单独蒸汽压缩机流程图

    SteamComp = FancyBboxPatch((0.4, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(SteamComp)

    ax.text(0.3, 0.85, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
    # 可变文字部分，根据用户输入来显示
    ax.text(0.5, 0.7, '蒸汽压缩机', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.55, 0.4, '耗电量：'+str(round(StCompElect,0))+'kW', ha='center', va='center', fontsize=8)


    arrowTG1 = Arrow(0.2, 0.8, 0.2, 0, width=0.05, color='#00CED1')
    arrowTout2 = Arrow(0.6, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowEle = Arrow(0.45, 0.35, 0, 0.15, width=0.05, color='#FF8C00')

    # 将箭头添加到图表上
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowEle)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')

def create_CentrifugalHeatPump(TG1,TG2,Tout1,Tout2,StCompElect,ax):

    CentrifugalHeatPump = FancyBboxPatch((0.4, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(CentrifugalHeatPump)

    # 在方块上添加文字
    # 'ax.text' 在指定位置添加文字
    # 参数分别为：x坐标，y坐标，文字内容，水平对齐方式，垂直对齐方式，字体大小
    ax.text(0.3, 0.85, '余热出口：'+str(TG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.3, 0.6, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
 
    # 可变文字部分，根据用户输入来显示
    ax.text(0.5, 0.7, '离心式热泵', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.55, '补水：'+str(Tout1)+'℃', ha='center', va='center', fontsize=8)   
    ax.text(0.7, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.3, '耗电量：'+str(round(StCompElect,0))+'kW', ha='center', va='center', fontsize=8)

    arrowTG2 = Arrow(0.4, 0.8, -0.2, 0, width=0.05, color='#00CED1')
    arrowTG1 = Arrow(0.2, 0.55, 0.2, 0, width=0.05, color='#00CED1')
    arrowTout1 = Arrow(0.8, 0.6, -0.2, 0, width=0.05, color='#FF0000')
    arrowTout2 = Arrow(0.6, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowEle = Arrow(0.5, 0.35, 0, 0.15, width=0.05, color='#FF8C00')


    # 将箭头添加到图表上
    ax.add_patch(arrowTG2)
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowTout1)
    ax.add_patch(arrowEle)

    # 设置图表的显示范围和关闭坐标轴
    # 'set_xlim' 和 'set_ylim' 设置x轴和y轴的显示范围
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')    

def create_Abs_SteamCompressor_flowchart(TG1,TG2,Tmiddle,Tout1,Tout2,StCompElect,TW1,TW2,ax):#吸收式热泵串联蒸汽压缩机流程图
    # 绘制流程图中的方块（节点）
    # 'FancyBboxPatch' 创建一个带圆角的方块
    # 参数分别为：位置坐标（x, y），宽度，高度，圆角样式，颜色
    Abs = FancyBboxPatch((0.2, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")
    SteamComp = FancyBboxPatch((0.6, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(Abs)
    ax.add_patch(SteamComp)


    ax.text(0.1, 0.85, '余热出口：'+str(TG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.1, 0.6, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.85, '中间蒸汽：'+str(Tmiddle)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.55, '补水：'+str(Tout1)+'℃', ha='center', va='center', fontsize=8)   
    ax.text(0.9, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.6, 0.3, '耗电量'+str(round(StCompElect,0))+'kW', va='center', fontsize=8)
    ax.text(0.3, 0.3, '冷却水温度：'+str(TW1)+'-'+str(TW2)+'℃', ha='center', va='center', fontsize=8)
    
    ax.text(0.3, 0.7, '吸收式热泵', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.7, '蒸汽压缩机', ha='center', va='center', fontsize=12)

    arrowTG1 = Arrow(0.0, 0.55, 0.2, 0, width=0.05, color='#00CED1')
    arrowTG2 = Arrow(0.2, 0.8, -0.2, 0, width=0.05, color='#00CED1')
    arrowMiddle = Arrow(0.4, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTout1 = Arrow(0.5, 0.6, -0.1, 0, width=0.05, color='#FF0000')
    arrowTout2 = Arrow(0.8, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTW1 = Arrow(0.25, 0.35, 0, 0.15, width=0.05, color='#3CB371')
    arrowTW2 = Arrow(0.35, 0.5, 0, -0.15, width=0.05, color='#3CB371')
    arrowEle = Arrow(0.65, 0.35, 0, 0.15, width=0.05, color='#FF8C00')

    # 将箭头添加到图表上
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTG2)
    ax.add_patch(arrowMiddle)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowTout1)
    ax.add_patch(arrowTW1)
    ax.add_patch(arrowTW2)
    ax.add_patch(arrowEle)

    # 设置图表的显示范围和关闭坐标轴
    # 'set_xlim' 和 'set_ylim' 设置x轴和y轴的显示范围
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')

def create_CentHeatPump_SteamComp(TG1,TG2,Tmiddle,Tout1,Tout2,CtHeatPumpElect2,StCompElect,ax):

    CentrifugalHeatPump = FancyBboxPatch((0.2, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")
    SteamComp = FancyBboxPatch((0.6, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(CentrifugalHeatPump)
    ax.add_patch(SteamComp)

    ax.text(0.1, 0.85, '余热出口：'+str(TG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.1, 0.6, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.85, '中间蒸汽：'+str(Tmiddle)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.55, '补水：'+str(Tout1)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.9, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.2, 0.3, '耗电量'+str(round(CtHeatPumpElect2,0))+'kW', va='center', fontsize=8)    
    ax.text(0.6, 0.3, '耗电量'+str(round(StCompElect,0))+'kW', va='center', fontsize=8)
    
    ax.text(0.3, 0.7, '离心式热泵', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.7, '蒸汽压缩机', ha='center', va='center', fontsize=12)

    arrowTG1 = Arrow(0.0, 0.55, 0.2, 0, width=0.05, color='#00CED1')
    arrowTG2 = Arrow(0.2, 0.8, -0.2, 0, width=0.05, color='#00CED1')
    arrowMiddle = Arrow(0.4, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTout2 = Arrow(0.8, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTout1 = Arrow(0.5, 0.6, -0.1, 0, width=0.05, color='#FF0000')
    arrowEle1 = Arrow(0.25, 0.35, 0, 0.15, width=0.05, color='#FF8C00')
    arrowEle2 = Arrow(0.65, 0.35, 0, 0.15, width=0.05, color='#FF8C00')

    # 将箭头添加到图表上
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTG2)
    ax.add_patch(arrowMiddle)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowTout1)
    ax.add_patch(arrowEle1)
    ax.add_patch(arrowEle2)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')

def create_FlashEva_SteamComp(TG1,TG2,FalshEvapTG2,Tout1,Tout2,FalshEvapElect,StCompElect3,ax):
    # 绘制流程图中的方块（节点）
    # 'FancyBboxPatch' 创建一个带圆角的方块
    # 参数分别为：位置坐标（x, y），宽度，高度，圆角样式，颜色
    FlashEvaporation = FancyBboxPatch((0.2, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")
    SteamComp = FancyBboxPatch((0.6, 0.5), 0.2, 0.4, boxstyle="round,pad=0.01", color="#FFD700")

    # 将方块添加到图表上
    ax.add_patch(FlashEvaporation)
    ax.add_patch(SteamComp)

    ax.text(0.1, 0.85, '余热出口：'+str(TG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.1, 0.6, '余热入口：'+str(TG1)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.5, 0.85, '中间蒸汽：'+str(FalshEvapTG2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.9, 0.85, '产出蒸汽：'+str(Tout2)+'℃', ha='center', va='center', fontsize=8)
    ax.text(0.2, 0.3, '耗电量'+str(round(FalshEvapElect,0))+'kW', va='center', fontsize=8)    
    ax.text(0.6, 0.3, '耗电量'+str(round(StCompElect3,0))+'kW', va='center', fontsize=8)
    
    ax.text(0.3, 0.7, '闪蒸罐', ha='center', va='center', fontsize=12)
    ax.text(0.7, 0.7, '蒸汽压缩机', ha='center', va='center', fontsize=12)

    arrowTG1 = Arrow(0.0, 0.55, 0.2, 0, width=0.05, color='#00CED1')
    arrowTG2 = Arrow(0.2, 0.8, -0.2, 0, width=0.05, color='#00CED1')
    arrowMiddle = Arrow(0.4, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowTout2 = Arrow(0.8, 0.8, 0.2, 0, width=0.05, color='#FF0000')
    arrowEle1 = Arrow(0.25, 0.35, 0, 0.15, width=0.05, color='#FF8C00')
    arrowEle2 = Arrow(0.65, 0.35, 0, 0.15, width=0.05, color='#FF8C00')

    # 将箭头添加到图表上
    ax.add_patch(arrowTG1)
    ax.add_patch(arrowTG2)
    ax.add_patch(arrowMiddle)
    ax.add_patch(arrowTout2)
    ax.add_patch(arrowEle1)
    ax.add_patch(arrowEle2)


    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    # 'axis' 设置为'off'关闭坐标轴显示
    ax.axis('off')


def main():
    st.title('余热产蒸汽系统')
    with st.sidebar:
        st.header('输入参数')
        input_variables = {}
        col0,col1 = st.columns(2)
        with col0:
            input_variables['HeatSourceType'] = st.radio( "请选择余热类型：", ('蒸汽', '热水'))
        with col1:
            input_variables['HeatSourceFlow'] = st.number_input('余热流量t/h:', value=25.0, step=1.0)

        col0, col1= st.columns(2)
        with col0:
            input_variables['TG1'] = st.number_input('余热入口温度:', value=90.0, step=1.0)
            input_variables['TW1'] = st.number_input('冷却水入口:', value=32.0, step=1.0)
            input_variables['Tout1'] = st.number_input('补水温度:', value=90.0, step=1.0)

        with col1: # 第一列
            input_variables['TG2'] = st.number_input('余热出口温度:', value=80.0, step=1.0)            
            input_variables['TW2'] = st.number_input('冷却水出口:', value=40.0, step=1.0)
            input_variables['Tout2'] = st.number_input('产出温度:', value=120.0, step=1.0)
        
        cola, colb= st.columns(2)
        with cola: # 第1列
            input_variables['AnnualOperatingHours'] = st.number_input('年运行时长 h', value=8000.0, step=1.0)
            input_variables['SteamUnitPrice'] = st.number_input('蒸汽单价 元/吨:', value=100.0, step=1.0)
        with colb: # 第2列
            input_variables['ElectricityUnitPrice'] = st.number_input('电价:', value=0.5, step=0.1)
            input_variables['CoolingWaterUnitPrice'] = st.number_input('冷却水单价:', value=0.4, step=0.1)
        instructions = (                                                                    #使用说明
                        "1.该工具从余热量推算制热量，制取饱和蒸汽，流量单位均为t/h;<br>"
                        "2.余热类型选择蒸汽或热水，余热品味均以温度表示，热源蒸汽为饱和蒸汽;<br>"
                        "3.如果余热为蒸汽，则余热出口为与入口温度相同的饱和水;<br>"
                        "4.第二类吸收式热泵需要冷却水;<br>"
                        "5.涉及到双设备串联的系统，需要手动调整串联设备时间的‘中间温度’;<br>"
                        "6.如果需要计算投资回报期，则需要输入设备投资成本;<br>"
                        "7.如有使用问题，或有功能需求，联系 国志鹏 。<br>"
                        "————2024-10-08"
                        )
                        
        st.markdown("___")
        st.write('使用说明：')
        st.caption(instructions, unsafe_allow_html=True)
    if input_variables['HeatSourceType'] is not None:
        HeatSourceType=input_variables['HeatSourceType']
        TG1=input_variables['TG1']
        TG2=input_variables['TG2']
        Tout1=input_variables['Tout1']
        Tout2=input_variables['Tout2']
        HeatSourceFlow=input_variables['HeatSourceFlow']
        AnnualOperatingHours=input_variables['AnnualOperatingHours']
        ElectricityUnitPrice=input_variables['ElectricityUnitPrice']
        SteamUnitPrice=input_variables['SteamUnitPrice']
        CoolingWaterUnitPrice=input_variables['CoolingWaterUnitPrice']
        TW1=input_variables['TW1']
        TW2=input_variables['TW2']

    if HeatSourceType == '蒸汽':
        TG2=TG1
        #单独吸收式热泵
        st.subheader('单独吸收式热泵')
        AbsAloneResult = AbsorptionHeatPump(HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if AbsAloneResult['model'] == 1:
            input_variables['ABsInvestmentCost'] = st.number_input('吸收式热泵投资成本 万元', value=0.0, step=100.0,key='吸收式热泵投资成本 万元')
            AbsAStreamFlow = AbsAloneResult['蒸汽流量']
            AbsACoolingWaterFlow = AbsAloneResult['冷却水流量']
            AbsACoolingWaterCost = AbsAloneResult['冷却水成本']
            AbsSteamCost = AbsAloneResult['产蒸汽收益']
            AbsNetIncome = AbsAloneResult['净收益']
            AbsNetIncomePerStream = AbsAloneResult['每吨蒸汽收益']
            PaybackPeriodAbs = input_variables['ABsInvestmentCost']/AbsNetIncome #回报期 年
            # 创建一个包含三个列的列表显示
            cols = st.columns(4)
            # 第一行
            cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(AbsAloneResult['蒸汽流量']))
            cols[1].metric(label="冷却水流量", value='{:.0f}'.format(AbsAloneResult['冷却水流量']))
            cols[2].metric(label="净收益 万元", value='{:.0f}'.format(AbsAloneResult['净收益']))
            cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodAbs))

            # 第二行
            cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(AbsAloneResult['产蒸汽收益']))
            cols[1].metric(label="冷却水成本 万元", value='{:.0f}'.format(AbsAloneResult['冷却水成本']))
            cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(AbsAloneResult['每吨蒸汽收益']))   
            # 使用用户输入的文字创建流程图
            fig, ax = plt.subplots(figsize=(6, 2))
            create_Abs_flowchart(TG1,TG2,Tout1,Tout2,TW1,TW2, ax)
            st.pyplot(fig)
        else:
            st.write(AbsAloneResult['Errordata'])
        st.markdown("___")
        st.subheader('单独蒸汽压缩机')
        SteamCompressorAloneResult = SteamCompressor(HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if SteamCompressorAloneResult['model'] == 1:
            input_variables['StCpInvestmentCost'] = st.number_input('蒸汽压缩机投资成本 万元', value=0.0, step=100.0,key='蒸汽压缩机投资成本 万元')            
            StCompStreamFlow = SteamCompressorAloneResult['蒸汽流量']
            StCompElect = SteamCompressorAloneResult['耗电量']
            StCompOperatingCost = SteamCompressorAloneResult['耗电成本']
            StCompSteamCost = SteamCompressorAloneResult['产蒸汽收益']
            StCompNetIncome = SteamCompressorAloneResult['净收益']
            StCompNetIncomePerStream = SteamCompressorAloneResult['每吨蒸汽收益']
            StCompStageNumber = SteamCompressorAloneResult['级数']
            PaybackPeriodSteamCompressor = input_variables['StCpInvestmentCost']/StCompNetIncome #回报期 年

            cols = st.columns(4)
            # 第一行
            cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(SteamCompressorAloneResult['蒸汽流量']))
            cols[1].metric(label="耗电量 kW", value='{:.0f}'.format(SteamCompressorAloneResult['耗电量']))
            cols[2].metric(label="净收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult['净收益']))
            cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodSteamCompressor))

            # 第二行
            cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult['产蒸汽收益']))
            cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(SteamCompressorAloneResult['耗电成本']))
            cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult['每吨蒸汽收益']))
            cols[3].metric(label="级数", value='{:.0f}'.format(SteamCompressorAloneResult['级数']))
            # 使用用户输入的文字创建流程图
            fig, ax = plt.subplots(figsize=(6, 2))
            create_SteamCompressor_flowchart(TG1,TG2,Tout2,StCompElect, ax)
            st.pyplot(fig)
        else:
            st.write(SteamCompressorAloneResult['Errordata'])
        
        st.markdown("___")
        st.subheader('吸收式热泵串联蒸汽压缩机')
        colsInvestmentCost = st.columns(3)
        # 第一行
        with colsInvestmentCost[0]:
            input_variables['ABsInvestmentCost2'] = st.number_input('吸收式热泵投资成本 万元', value=0.0, step=100.0,key='吸收式热泵投资成本2 万元')
        with colsInvestmentCost[1]:
            input_variables['StCpInvestmentCost2'] = st.number_input('蒸汽压缩机投资成本 万元', value=0.0, step=100.0,key='蒸汽压缩机2投资成本2 万元')
        with colsInvestmentCost[2]:
            input_variables['Tmiddle'] = st.number_input('中间温度 ℃', value=TG2+40, step=1.0)

        AbsAloneResult2 = AbsorptionHeatPump(HeatSourceType,TG1,TG2,Tout1,input_variables['Tmiddle'],HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if AbsAloneResult2['model']==1:    
            AbsAStreamFlow2 = AbsAloneResult2['蒸汽流量']
            AbsACoolingWaterFlow2 = AbsAloneResult2['冷却水流量']
            AbsACoolingWaterCost2 = AbsAloneResult2['冷却水成本']
            AbsSteamCost2 = AbsAloneResult2['产蒸汽收益']
            AbsNetIncome2 = AbsAloneResult2['净收益']
            AbsNetIncomePerStream2 = AbsAloneResult2['每吨蒸汽收益']
            SteamCompressorAloneResult2 = SteamCompressor(HeatSourceType,input_variables['Tmiddle'],TG2,Tout1,Tout2,AbsAStreamFlow2,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
            if SteamCompressorAloneResult2['model']==1:
                StCompStreamFlow2 = SteamCompressorAloneResult2['蒸汽流量']
                StCompElect2 = SteamCompressorAloneResult2['耗电量']
                StCompOperatingCost2 = SteamCompressorAloneResult2['耗电成本']
                StCompSteamCost2 = SteamCompressorAloneResult2['产蒸汽收益']
                StCompNetIncome2 = SteamCompressorAloneResult2['净收益']
                StCompStageNumber2 = SteamCompressorAloneResult2['级数']
                StCompNetIncome2=StCompNetIncome2-AbsACoolingWaterCost2 #压缩机蒸汽收益减去二类热泵循环水成本
                StCompNetIncomePerStream2=StCompNetIncome2/StCompStreamFlow2 #重新计算每吨蒸汽收益
                PaybackPeriodAbsAndStComp = (input_variables['ABsInvestmentCost2']+input_variables['StCpInvestmentCost2'])/StCompNetIncome2 #回报期 年

                cols = st.columns(4)
                # 第一行
                cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(SteamCompressorAloneResult2['蒸汽流量']))
                cols[1].metric(label="耗电量 kW", value='{:.0f}'.format(SteamCompressorAloneResult2['耗电量']))
                cols[2].metric(label="净收益 万元", value='{:.0f}'.format(StCompNetIncome2))
                cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodAbsAndStComp))

                # 第二行
                cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult2['产蒸汽收益']))
                cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(SteamCompressorAloneResult2['耗电成本']))
                cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(StCompNetIncomePerStream2))
                # 第三行
                cols[0].metric(label="级数", value='{:.0f}'.format(SteamCompressorAloneResult2['级数']))
                cols[1].metric(label="冷却水流量", value='{:.0f}'.format(AbsAloneResult2['冷却水流量']))
                cols[2].metric(label="冷却水成本 万元", value='{:.0f}'.format(AbsAloneResult2['冷却水成本']))
                # 使用用户输入的文字创建流程图
                fig, ax = plt.subplots(figsize=(6, 2))
                create_Abs_SteamCompressor_flowchart(TG1,TG2,input_variables['Tmiddle'],Tout1,Tout2,StCompElect2,TW1,TW2,ax)
                st.pyplot(fig)
            else :
                st.write(SteamCompressorAloneResult2['Errordata'])
        else :
            st.write(AbsAloneResult2['Errordata'])

    elif HeatSourceType == '热水':
            #单独吸收式热泵
        st.subheader('单独吸收式热泵')
        AbsAloneResult = AbsorptionHeatPump(HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if AbsAloneResult['model']==1:
            AbsAStreamFlow = AbsAloneResult['蒸汽流量']
            AbsACoolingWaterFlow = AbsAloneResult['冷却水流量']
            AbsACoolingWaterCost = AbsAloneResult['冷却水成本']
            AbsSteamCost = AbsAloneResult['产蒸汽收益']
            AbsNetIncome = AbsAloneResult['净收益']
            AbsNetIncomePerStream = AbsAloneResult['每吨蒸汽收益']
            input_variables['ABsInvestmentCost3'] = st.number_input('吸收式热泵投资成本 万元', value=0.0, step=100.0,key='吸收式热泵投资成本 万元')
            PaybackPeriodAbs = input_variables['ABsInvestmentCost3']/AbsNetIncome #回报期 年

            # 创建一个包含三个列的列表显示
            cols = st.columns(4)
            # 第一行
            cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(AbsAloneResult['蒸汽流量']))
            cols[1].metric(label="冷却水流量", value='{:.0f}'.format(AbsAloneResult['冷却水流量']))
            cols[2].metric(label="净收益 万元", value='{:.0f}'.format(AbsAloneResult['净收益']))
            cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodAbs))

            # 第二行
            cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(AbsAloneResult['产蒸汽收益']))
            cols[1].metric(label="冷却水成本 万元", value='{:.0f}'.format(AbsAloneResult['冷却水成本']))
            cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(AbsAloneResult['每吨蒸汽收益']))
                        # 使用用户输入的文字创建流程图
            fig, ax = plt.subplots(figsize=(6, 2))
            create_Abs_flowchart(TG1,TG2,Tout1,Tout2,TW1,TW2, ax)
            st.pyplot(fig)
        else :
            st.write(AbsAloneResult['Errordata'])

        st.markdown("___")
        st.subheader('单独离心热泵')
        CtHeatPumpResult = CentrifugalHeatPump(HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if CtHeatPumpResult['model']==1:
            #单独离心热泵
            input_variables['HeatPumpInvestmentCost2'] = st.number_input('离心式热泵投资成本 万元', value=0.0, step=100.0,key='离心式热泵投资成本 万元')

            CtHeatPumpStreamFlow = CtHeatPumpResult['蒸汽流量']
            CtHeatPumpElect = CtHeatPumpResult['耗电量']
            CtHeatPumpOperatingCost = CtHeatPumpResult['耗电成本']
            CtHeatPumpSteamCost = CtHeatPumpResult['产蒸汽收益']
            CtHeatPumpNetIncome = CtHeatPumpResult['净收益']
            CtHeatPumpNetIncomePerStream = CtHeatPumpResult['每吨蒸汽收益']
            PaybackPeriodCt = input_variables['HeatPumpInvestmentCost2']/CtHeatPumpNetIncome #回报期 年   

            cols = st.columns(4)
            # 第一行
            cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(CtHeatPumpResult['蒸汽流量']))
            cols[1].metric(label="耗电量", value='{:.0f}'.format(CtHeatPumpResult['耗电量']))
            cols[2].metric(label="净收益 万元", value='{:.0f}'.format(CtHeatPumpResult['净收益']))
            cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodCt))

            # 第二行
            cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(CtHeatPumpResult['产蒸汽收益']))
            cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(CtHeatPumpResult['耗电成本']))
            cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(CtHeatPumpResult['每吨蒸汽收益']))
            cols[3].metric(label="离心热泵COP", value='{:.0f}'.format(CtHeatPumpResult['COP']))
            # 使用用户输入的文字创建流程图
            fig, ax = plt.subplots(figsize=(6, 2))
            create_CentrifugalHeatPump(TG1,TG2,Tout1,Tout2,CtHeatPumpElect, ax)
            st.pyplot(fig)
        else :
            st.write(CtHeatPumpResult['Errordata'])


        st.markdown("___")
        st.subheader('吸收式热泵串联蒸汽压缩机') #吸收式热泵串联蒸汽压缩机
        colsInvestmentCost = st.columns(3)
        with colsInvestmentCost[0]:
            input_variables['ABsInvestmentCost4'] = st.number_input('吸收式热泵投资成本 万元', value=0.0, step=100.0,key='吸收式热泵投资成本3 万元')
        with colsInvestmentCost[1]:
            input_variables['StCpInvestmentCost4'] = st.number_input('蒸汽压缩机投资成本 万元', value=0.0, step=100.0,key='蒸汽压缩机投资成本3 万元')
        with colsInvestmentCost[2]:
            input_variables['Tmiddle'] = st.number_input('中间温度 ℃', value=TG2+40, step=1.0,key='中间温度2 ℃')
        AbsAloneResult2 = AbsorptionHeatPump(HeatSourceType,TG1,TG2,Tout1,input_variables['Tmiddle'],HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if AbsAloneResult2['model']==1:
            AbsAStreamFlow2 = AbsAloneResult2['蒸汽流量']
            AbsACoolingWaterFlow2 = AbsAloneResult2['冷却水流量']
            AbsACoolingWaterCost2 = AbsAloneResult2['冷却水成本']
            AbsSteamCost2 = AbsAloneResult2['产蒸汽收益']
            AbsNetIncome2 = AbsAloneResult2['净收益']
            AbsNetIncomePerStream2 = AbsAloneResult2['每吨蒸汽收益']
            SteamCompressorAloneResult22 = SteamCompressor(HeatSourceType,input_variables['Tmiddle'],TG2,Tout1,Tout2,AbsAStreamFlow2,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
            if SteamCompressorAloneResult22['model'] == 1:
                StCompStreamFlow2 = SteamCompressorAloneResult22['蒸汽流量']
                StCompElect2 = SteamCompressorAloneResult22['耗电量']
                StCompOperatingCost2 = SteamCompressorAloneResult22['耗电成本']
                StCompSteamCost2 = SteamCompressorAloneResult22['产蒸汽收益']
                StCompNetIncome2 = SteamCompressorAloneResult22['净收益']
                StCompNetIncomePerStream2 = SteamCompressorAloneResult22['每吨蒸汽收益']
                StCompStageNumber2 = SteamCompressorAloneResult22['级数']
                StCompNetIncome2=StCompNetIncome2-AbsACoolingWaterCost2 #压缩机蒸汽收益减去二类热泵循环水成本
                StCompNetIncomePerStream2=StCompNetIncome2/StCompStreamFlow2 #重新计算每吨蒸汽收益
                PaybackPeriodAbsAndStComp = (input_variables['ABsInvestmentCost4']+input_variables['StCpInvestmentCost4'])/StCompNetIncome2 #回报期 年

                cols = st.columns(4)
                # 第一行
                cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(SteamCompressorAloneResult22['蒸汽流量']))
                cols[1].metric(label="耗电量", value='{:.0f}'.format(SteamCompressorAloneResult22['耗电量']))
                cols[2].metric(label="净收益 万元", value='{:.0f}'.format(StCompNetIncome2))
                cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodAbsAndStComp))

                # 第二行
                cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult22['产蒸汽收益']))
                cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(SteamCompressorAloneResult22['耗电成本']))
                cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(StCompNetIncomePerStream2))
                # 第三行
                cols[0].metric(label="级数", value='{:.0f}'.format(SteamCompressorAloneResult22['级数']))
                cols[1].metric(label="冷却水流量", value='{:.0f}'.format(AbsAloneResult2['冷却水流量']))
                cols[2].metric(label="冷却水成本 万元", value='{:.0f}'.format(AbsAloneResult2['冷却水成本']))
                # 使用用户输入的文字创建流程图
                fig, ax = plt.subplots(figsize=(6, 2))
                create_Abs_SteamCompressor_flowchart(TG1,TG2,input_variables['Tmiddle'],Tout1,Tout2,StCompElect2,TW1,TW2,ax)
                st.pyplot(fig)
            else:
                st.write(SteamCompressorAloneResult22['Errordata'])
        else:
            st.write(AbsAloneResult2['Errordata'])

        st.markdown("___")
        st.subheader('离心热泵串联蒸汽压缩机')            #离心热泵串联蒸汽压缩机
        colsInvestmentCost = st.columns(3)
        # 第一行
        with colsInvestmentCost[0]:
            input_variables['HeatPumpInvestmentCost5'] = st.number_input('离心热泵投资成本 万元', value=0.0, step=100.0,key='离心热泵投资成本4 万元')
        with colsInvestmentCost[1]:
            input_variables['StCpInvestmentCost5'] = st.number_input('蒸汽压缩机投资成本 万元', value=0.0, step=100.0,key='蒸汽压缩机投资成本4 万元')
        with colsInvestmentCost[2]:
            input_variables['Tmiddle'] = st.number_input('中间温度 ℃', value=TG2+20, step=1.0,key='中间温度3 ℃')
        CtHeatPumpResult2 = CentrifugalHeatPump(HeatSourceType,TG1,TG2,Tout1,input_variables['Tmiddle'],HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if CtHeatPumpResult2['model']==1:
            CtHeatPumpStreamFlow2 = CtHeatPumpResult2['蒸汽流量']
            CtHeatPumpElect2 = CtHeatPumpResult2['耗电量']
            CtHeatPumpOperatingCost2 = CtHeatPumpResult2['耗电成本']
            CtHeatPumpSteamCost2 = CtHeatPumpResult2['产蒸汽收益']
            CtHeatPumpNetIncome2 = CtHeatPumpResult2['净收益']
            CtHeatPumpNetIncomePerStream2 = CtHeatPumpResult2['每吨蒸汽收益']
            SteamCompressorAloneResult = SteamCompressor(HeatSourceType,input_variables['Tmiddle'],TG2,Tout1,Tout2,CtHeatPumpStreamFlow2,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
            if SteamCompressorAloneResult['model']==1:
                StCompStreamFlow = SteamCompressorAloneResult['蒸汽流量']
                StCompElect = SteamCompressorAloneResult['耗电量']
                StCompOperatingCost = SteamCompressorAloneResult['耗电成本']
                StCompSteamCost = SteamCompressorAloneResult['产蒸汽收益']
                StCompNetIncome = SteamCompressorAloneResult['净收益']
                StCompNetIncomePerStream = SteamCompressorAloneResult['每吨蒸汽收益']
                StCompStageNumber = SteamCompressorAloneResult['级数']
                StCompNetIncome=StCompNetIncome-CtHeatPumpOperatingCost2 #压缩机蒸汽收益减去离心热泵耗电成本
                StCompNetIncomePerStream=StCompNetIncome/StCompStreamFlow#重新计算每吨蒸汽收益
                TotalElect = CtHeatPumpElect2 + StCompElect #总耗电量
                TotalOperatingCost = CtHeatPumpOperatingCost2 + StCompOperatingCost #总耗电成本
                PaybackPeriodAbsAndStComp22 = (input_variables['HeatPumpInvestmentCost5']+input_variables['StCpInvestmentCost5'])/StCompNetIncome #回报期 年


                cols = st.columns(4)
                # 第一行
                cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(SteamCompressorAloneResult['蒸汽流量']))
                cols[1].metric(label="耗电量 万元", value='{:.0f}'.format(TotalElect))
                cols[2].metric(label="净收益 万元", value='{:.0f}'.format(StCompNetIncome))
                cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodAbsAndStComp22))

                # 第二行
                cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult['产蒸汽收益']))
                cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(TotalOperatingCost))
                cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(StCompNetIncomePerStream))
                # 第三行
                cols[0].metric(label="级数", value='{:.0f}'.format(SteamCompressorAloneResult['级数']))
                cols[1].metric(label="离心热泵COP", value='{:.0f}'.format(CtHeatPumpResult2['COP']))
                # 使用用户输入的文字创建流程图
                fig, ax = plt.subplots(figsize=(6, 2))
                create_CentHeatPump_SteamComp(TG1,TG2,input_variables['Tmiddle'],Tout1,Tout2,CtHeatPumpElect2,StCompElect,ax)
                st.pyplot(fig)
            else:
                st.write(SteamCompressorAloneResult['Errordata'])
        else:
            st.write(CtHeatPumpResult2['Errordata'])


        #闪蒸串联蒸汽压缩机
        st.markdown("___")
        st.subheader('闪蒸串联蒸汽压缩机')
        colsInvestmentCost = st.columns(2)
        # 第一行
        with colsInvestmentCost[0]:
            input_variables['FlashEvaporation'] = st.number_input('闪蒸系统投资成本 万元', value=0.0, step=100.0,key='闪蒸系统投资成本6 万元')
        with colsInvestmentCost[1]:
            input_variables['StCpInvestmentCost6'] = st.number_input('蒸汽压缩机投资成本 万元', value=0.0, step=100.0,key='蒸汽压缩机2投资成本6 万元')

        FlashEvaResult = FlashEvaporation (HeatSourceType,TG1,TG2,Tout1,Tout2,HeatSourceFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
        if FlashEvaResult['model']==1:        
            FalshEvapStreamFlow = FlashEvaResult['蒸汽流量']
            FalshEvapTG2 = FlashEvaResult['蒸汽温度']
            FalshEvapElect = FlashEvaResult['耗电量']
            FalshEvapOperatingCost = FlashEvaResult['耗电成本']
            SteamCompressorAloneResult3 = SteamCompressor(HeatSourceType,FalshEvapTG2,FalshEvapTG2,Tout1,Tout2,FalshEvapStreamFlow,AnnualOperatingHours,ElectricityUnitPrice,SteamUnitPrice,CoolingWaterUnitPrice,TW1,TW2)
            if SteamCompressorAloneResult3['model'] == 1:
                StCompStreamFlow3 = SteamCompressorAloneResult3['蒸汽流量']
                StCompElect3 = SteamCompressorAloneResult3['耗电量']
                StCompOperatingCost3 = SteamCompressorAloneResult3['耗电成本']
                StCompSteamCost3 = SteamCompressorAloneResult3['产蒸汽收益']
                StCompNetIncome3 = SteamCompressorAloneResult3['净收益']
                StCompNetIncomePerStream3 = SteamCompressorAloneResult3['每吨蒸汽收益']
                StCompStageNumber3 = SteamCompressorAloneResult3['级数']
                StCompNetIncome3=StCompNetIncome3-FalshEvapOperatingCost #压缩机蒸汽收益减去离心热泵耗电成本
                StCompNetIncomePerStream3=StCompNetIncome3/StCompStreamFlow3 #重新计算每吨蒸汽收益
                TotalElect3 = FalshEvapElect + StCompElect3 #总耗电量
                TotalOperatingCost3 = FalshEvapOperatingCost + StCompOperatingCost3 #总耗电成本
                PaybackPeriodFlashAndStComp= (input_variables['FlashEvaporation']+input_variables['StCpInvestmentCost6'])/StCompNetIncome3 #回报期 年
                
                cols = st.columns(4)
                # 第一行
                cols[0].metric(label="蒸汽流量t/h", value='{:.2f}'.format(SteamCompressorAloneResult3['蒸汽流量']))
                cols[1].metric(label="耗电量", value='{:.0f}'.format(TotalElect3))
                cols[2].metric(label="净收益 万元", value='{:.0f}'.format(StCompNetIncome3))
                cols[3].metric(label="回报期 年", value='{:.2f}'.format(PaybackPeriodFlashAndStComp))

                # 第二行
                cols[0].metric(label="产蒸汽收益 万元", value='{:.0f}'.format(SteamCompressorAloneResult3['产蒸汽收益']))
                cols[1].metric(label="耗电成本 万元", value='{:.0f}'.format(TotalOperatingCost3))
                cols[2].metric(label="每吨蒸汽收益 万元", value='{:.0f}'.format(StCompNetIncomePerStream3))
                cols[3].metric(label="级数", value='{:.0f}'.format(SteamCompressorAloneResult3['级数']))
                # 使用用户输入的文字创建流程图
                fig, ax = plt.subplots(figsize=(6, 2))
                create_FlashEva_SteamComp(TG1,TG2,FalshEvapTG2,Tout1,Tout2,FalshEvapElect,StCompElect3,ax)
                st.pyplot(fig)
            else:
                st.write(SteamCompressorAloneResult3['Errordata'])
        else:
            st.write(FlashEvaResult['Errordata'])

if __name__ == '__main__':
    main()
