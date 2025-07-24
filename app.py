#补全数据，新数据源brokerSignal

# 导入需要的库
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from dash.dependencies import ALL

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取数据文件（使用新的文件路径）
df = pd.read_excel("brokerSignal.xlsx")

# ========== 数据预处理 ==========
df['日期'] = pd.to_datetime(df['日期'])
df['年份'] = df['日期'].dt.year

# 提取指标列（根据新数据源调整）
indicator_cols = [
    '中国大豆压榨企业原料大豆库存', '大豆港口库存', '大豆现货压榨利润', '大豆压榨盘面利润',
    '豆粕基差', '豆粕仓单', '豆粕库存', '豆菜价差', '生猪存栏', '日内动量', '双均线', 
    '中值双均线', '考夫曼均线', '顺势指标CCI', 'TRIX指标', '布林带', '波动趋势', '佳庆指标'
]

# 去除关键字段缺失值
df = df.dropna(subset=['持仓量', '变化率', '价格'])

# 合约名称排序
contract_order = df.groupby('合约名称')['日期'].min().sort_values().index.tolist()
df['合约名称'] = pd.Categorical(df['合约名称'], categories=contract_order, ordered=True)

# 转换多/空头和加/减仓编码为文字标签
df['多空标签'] = df['多/空头'].map({'l': '多头', 's': '空头'})
df['仓位动作标签'] = df['加/减仓'].map({1: '加仓', -1: '减仓', 0: '不变'})

# ========= 指标分组 =========
fundamental_signals = [
    "中国大豆压榨企业原料大豆库存", "大豆港口库存", "大豆现货压榨利润", "大豆压榨盘面利润",
    "豆粕基差", "豆粕仓单", "豆粕库存", "豆菜价差", "生猪存栏"
]
trend_indicators = ["双均线", "中值双均线", "考夫曼均线", "TRIX指标"]
oscillators = ["顺势指标CCI", "布林带", "日内动量"]
volume_indicators = ["佳庆指标", "波动趋势"]

# ========== 初始化 Dash App ==========
app = Dash(__name__)

# 应用布局设计
app.layout = html.Div([
    html.H2("豆粕持仓数据分析系统", style={"textAlign": "center"}),
    
    dcc.Dropdown(
        id='broker-dropdown',
        options=[{'label': name, 'value': name} for name in df['经纪商名称'].unique()],
        multi=True,
        placeholder='选择经纪商'
    ),

    dcc.Dropdown(
        id='year-dropdown',
        options=[{'label': str(y), 'value': y} for y in sorted(df['年份'].unique())],
        placeholder='选择年份'
    ),

    dcc.Dropdown(
        id='long-short-dropdown',
        options=[{'label': '多头', 'value': 'l'}, {'label': '空头', 'value': 's'}],
        placeholder='选择多/空头',
        multi=True
    ),

    dcc.Dropdown(
        id='action-dropdown',
        options=[{'label': '加仓', 'value': 1}, {'label': '减仓', 'value': -1}, {'label': '不变', 'value': 0}],
        placeholder='选择加/减仓',
        multi=True
    ),

    dcc.Dropdown(
        id='contract-dropdown',
        placeholder='选择合约名称'
    ),

    html.Hr(),

    dcc.Graph(id='holding-plot'),

    # 新增平滑控制
    html.Div([
        html.Label("平滑窗口大小(天):"),
        dcc.Slider(
            id='smoothing-window',
            min=1,
            max=30,
            step=1,
            value=7,  # 默认7天
            marks={i: str(i) for i in [1, 5, 10, 15, 20, 25, 30]},
        )
    ], style={'margin': '20px 0'}),

    dcc.Graph(id='change-rate-plot'),
    
    # 新增价格和价格变化率图表
    dcc.Graph(id='price-plot'),
    dcc.Graph(id='price-change-plot'),

    html.Hr(),

    # 新增显示控制开关
    html.Div([
        html.Label("显示控制:"),
        dcc.RadioItems(
            id='display-control',
            options=[
                {'label': '显示趋势线', 'value': 'trend'},
                {'label': '显示持仓曲线', 'value': 'holding'},
                {'label': '全部显示', 'value': 'all'}
            ],
            value='all',
            inline=True,
            style={'margin-left': '20px'}
        )
    ], style={'margin': '20px 0'}),
    html.Div(id='indicator-plots')

    # html.Hr(),
    # dcc.Graph(id='heatmap-all'),

    # html.Hr(),
    # html.H3("SHAP信号对加/减仓的解释强度"),
    # dcc.Graph(id='shap-action-heatmap')
])

# 更新多/空头下拉选项
@app.callback(
    Output('long-short-dropdown', 'options'),
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_long_short_dropdown(selected_brokers, selected_year):
    if not selected_brokers or not selected_year:
        return []
    
    filtered_df = df[(df['经纪商名称'].isin(selected_brokers)) & (df['年份'] == selected_year)]
    options = [{'label': '多头', 'value': 'l'}, {'label': '空头', 'value': 's'}]
    return options

# 更新加/减仓下拉选项
@app.callback(
    Output('action-dropdown', 'options'),
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('long-short-dropdown', 'value')]
)
def update_action_dropdown(selected_brokers, selected_year, selected_long_short):
    if not selected_brokers or not selected_year:
        return []
    
    filtered_df = df[(df['经纪商名称'].isin(selected_brokers)) & (df['年份'] == selected_year)]
    if selected_long_short:
        filtered_df = filtered_df[filtered_df['多/空头'].isin(selected_long_short)]
    
    options = [{'label': '加仓', 'value': 1}, {'label': '减仓', 'value': -1}, {'label': '不变', 'value': 0}]
    return options

# 更新合约名称下拉选项（按日期排序，基于所有筛选条件）
@app.callback(
    Output('contract-dropdown', 'options'),
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('long-short-dropdown', 'value'),
     Input('action-dropdown', 'value')]
)
def update_contract_dropdown(selected_brokers, selected_year, selected_long_short, selected_action):
    if not selected_brokers or not selected_year:
        return []
    
    filtered_df = df[(df['经纪商名称'].isin(selected_brokers)) & (df['年份'] == selected_year)]
    
    if selected_long_short:
        filtered_df = filtered_df[filtered_df['多/空头'].isin(selected_long_short)]
    
    if selected_action:
        filtered_df = filtered_df[filtered_df['加/减仓'].isin(selected_action)]
    
    contracts = filtered_df['合约名称'].dropna().unique().tolist()
    contracts_sorted = [c for c in contract_order if c in contracts]
    return [{'label': c, 'value': c} for c in contracts_sorted]

# 更新主图
@app.callback(
    [Output('holding-plot', 'figure'),
     Output('change-rate-plot', 'figure'),
     Output('price-plot', 'figure'),
     Output('price-change-plot', 'figure')],
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('long-short-dropdown', 'value'),
     Input('action-dropdown', 'value'),
     Input('contract-dropdown', 'value'),
     Input('smoothing-window', 'value')]
)
def update_main_plots(selected_brokers, selected_year, selected_long_short, 
                     selected_action, selected_contract, window_size):
    if not selected_brokers or not selected_year or not selected_contract:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()
    
    dff = df[(df['经纪商名称'].isin(selected_brokers)) & 
             (df['年份'] == selected_year) & 
             (df['合约名称'] == selected_contract)].copy()
    
    if selected_long_short:
        dff = dff[dff['多/空头'].isin(selected_long_short)]
    
    if selected_action:
        dff = dff[dff['加/减仓'].isin(selected_action)]
    
    # 添加多空标签和仓位动作标签到悬停文本
    hover_data = {'多空标签': True, '仓位动作标签': True, '日期': True}
    
    # 持仓量图表
    fig1 = px.line(dff, x='日期', y='持仓量', title='持仓量变化', 
                  hover_data=hover_data, markers=True)
    
    # 变化率图表添加平滑功能
    dff['平滑变化率'] = dff['变化率'].rolling(window=window_size, min_periods=1).mean()
    
    fig2 = go.Figure()
    # 原始变化率(半透明)
    fig2.add_trace(go.Scatter(
        x=dff['日期'], y=dff['变化率'],
        mode='lines+markers',
        name='原始变化率',
        line=dict(color='rgba(150,150,150,0.4)'),
        marker=dict(color='rgba(150,150,150,0.2)'),
        hoverinfo='text',
        text=[f"日期: {date}<br>原始变化率: {rate:.2%}<br>平滑变化率: {smooth:.2%}" 
              for date, rate, smooth in zip(dff['日期'], dff['变化率'], dff['平滑变化率'])]
    ))
    # 平滑变化率(突出显示)
    fig2.add_trace(go.Scatter(
        x=dff['日期'], y=dff['平滑变化率'],
        mode='lines',
        name=f'{window_size}天平滑',
        line=dict(color='red', width=2),
        hoverinfo='text',
        text=[f"日期: {date}<br>平滑变化率: {smooth:.2%}" 
              for date, smooth in zip(dff['日期'], dff['平滑变化率'])]
    ))
    
    fig2.update_layout(
        title=f'持仓变化率 ({window_size}天平滑)',
        yaxis_tickformat='.0%',
        hovermode='x unified',
        showlegend=True
    )
    
    # 价格图表
    fig3 = px.line(dff, x='日期', y='价格', title='价格变化',
                  hover_data=hover_data, markers=True)
    
    # 价格变化率图表
    dff['平滑价格变化率'] = dff['价格变化率'].rolling(window=window_size, min_periods=1).mean()
    
    fig4 = go.Figure()
    # 原始价格变化率(半透明)
    fig4.add_trace(go.Scatter(
        x=dff['日期'], y=dff['价格变化率'],
        mode='lines+markers',
        name='原始价格变化率',
        line=dict(color='rgba(150,150,150,0.4)'),
        marker=dict(color='rgba(150,150,150,0.2)'),
        hoverinfo='text',
        text=[f"日期: {date}<br>原始价格变化率: {rate:.2%}<br>平滑价格变化率: {smooth:.2%}" 
              for date, rate, smooth in zip(dff['日期'], dff['价格变化率'], dff['平滑价格变化率'])]
    ))
    # 平滑价格变化率(突出显示)
    fig4.add_trace(go.Scatter(
        x=dff['日期'], y=dff['平滑价格变化率'],
        mode='lines',
        name=f'{window_size}天平滑',
        line=dict(color='blue', width=2),
        hoverinfo='text',
        text=[f"日期: {date}<br>平滑价格变化率: {smooth:.2%}" 
              for date, smooth in zip(dff['日期'], dff['平滑价格变化率'])]
    ))
    
    fig4.update_layout(
        title=f'价格变化率 ({window_size}天平滑)',
        yaxis_tickformat='.0%',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig1, fig2, fig3, fig4

# 生成指标图（带持仓量曲线）
def generate_group_plots(dff, cols, title, display_mode):
    plots = []
    y_min = -1.25  # 固定指标Y轴范围
    y_max = 1.25
    
    # 计算持仓量的范围，用于右侧Y轴
    holding_min = dff['持仓量'].min()
    holding_max = dff['持仓量'].max()
    holding_range = holding_max - holding_min
    # 添加10%的边距
    holding_min = holding_min - 0.1 * holding_range if holding_range > 0 else holding_min * 0.9
    holding_max = holding_max + 0.1 * holding_range if holding_range > 0 else holding_max * 1.1
    
    for col in cols:
        fig = go.Figure()
        
        # 添加指标柱状图
        fig.add_trace(go.Bar(
            x=dff['日期'], 
            y=dff[col], 
            name=col, 
            marker_color='lightblue',
            hovertext=dff['多空标签'] + ', ' + dff['仓位动作标签']
        ))
        
        # 根据显示模式添加趋势线
        if display_mode in ['trend', 'all']:
            fig.add_trace(go.Scatter(
                x=dff['日期'], 
                y=dff[col].rolling(window=5).mean(),
                mode='lines', 
                name=f'{col}趋势线', 
                line=dict(color='rgba(255, 0, 0, 0.5)', width=1),
                yaxis='y1'
            ))
        
        # 根据显示模式添加持仓曲线
        if display_mode in ['holding', 'all']:
            fig.add_trace(go.Scatter(
                x=dff['日期'], 
                y=dff['持仓量'],
                mode='lines', 
                name='持仓量', 
                line=dict(color='green', width=2),
                yaxis='y2'
            ))
        
        # 更新布局
        fig.update_layout(
            title=col,
            height=300,
            margin=dict(l=30, r=60, t=40, b=30),
            showlegend=True,
            yaxis=dict(
                title='指标值',
                range=[y_min, y_max],
                side='left'
            ),
            yaxis2=dict(
                title='持仓量',
                range=[holding_min, holding_max],
                overlaying='y',
                side='right',
                showgrid=False
            )
        )
        
        plots.append(dcc.Graph(figure=fig))
    
    return html.Div([
        html.H4(title),
        html.Div(plots)
    ])

@app.callback(
    Output('indicator-plots', 'children'),
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('long-short-dropdown', 'value'),
     Input('action-dropdown', 'value'),
     Input('contract-dropdown', 'value'),
     Input('display-control', 'value')]
)
def generate_indicator_histograms(selected_brokers, selected_year, selected_long_short, selected_action, selected_contract, display_mode):
    if not selected_brokers or not selected_year or not selected_contract:
        return []
    
    dff = df[(df['经纪商名称'].isin(selected_brokers)) & 
             (df['年份'] == selected_year) & 
             (df['合约名称'] == selected_contract)]
    
    if selected_long_short:
        dff = dff[dff['多/空头'].isin(selected_long_short)]
    
    if selected_action:
        dff = dff[dff['加/减仓'].isin(selected_action)]
    
    plots = []
    plots.append(generate_group_plots(dff, fundamental_signals, "基本面信号", display_mode))
    plots.append(generate_group_plots(dff, trend_indicators, "趋势类指标", display_mode))
    plots.append(generate_group_plots(dff, oscillators, "震荡类指标", display_mode))
    plots.append(generate_group_plots(dff, volume_indicators, "量能类指标", display_mode))
    return plots

@app.callback(
    Output('heatmap-all', 'figure'),
    [Input('broker-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('long-short-dropdown', 'value'),
     Input('action-dropdown', 'value'),
     Input('contract-dropdown', 'value')]
)
def update_heatmap(selected_brokers, selected_year, selected_long_short, selected_action, selected_contract):
    if not selected_brokers or not selected_year or not selected_contract:
        return go.Figure()
    
    dff = df[(df['经纪商名称'].isin(selected_brokers)) & 
             (df['年份'] == selected_year) & 
             (df['合约名称'] == selected_contract)]
    
    if selected_long_short:
        dff = dff[dff['多/空头'].isin(selected_long_short)]
    
    if selected_action:
        dff = dff[dff['加/减仓'].isin(selected_action)]
    
    sub_df = dff[indicator_cols].dropna(how='all')
    if sub_df.empty:
        return go.Figure()
    
    corr_data = sub_df.corr()

    fig = px.imshow(
        corr_data,
        text_auto=".2f",
        color_continuous_scale='RdBu_r',
        zmin=-1,
        zmax=1,
        aspect="auto"
    )

    fig.update_layout(
        title="所有指标相关性热力图",
        height=1000,
        width=1200,
        font=dict(size=14),
        margin=dict(l=60, r=60, t=60, b=60)
    )

    return fig

# # 读取SHAP数据
# shap_summary_df = pd.read_csv("D:\\KaraJC的文件夹\\快学\\Intern\\LDC\\信号\\SHAP单权重，交互重要性\\SHAP百分比影响权重.csv")
# shap_summary_df.set_index(shap_summary_df.columns[0], inplace=True)

# @app.callback(
#     Output('shap-action-heatmap', 'figure'),
#     Input('contract-dropdown', 'value')
# )
# def display_shap_action_heatmap(contract):
#     fig = px.imshow(
#         shap_summary_df,
#         color_continuous_scale='Reds',
#         text_auto=".2f",
#         labels=dict(x="仓位行为", y="信号", color="平均SHAP值"),
#         aspect="auto"
#     )
#     fig.update_layout(title="各信号对加/减仓的解释强度（平均SHAP值）", height=800)
#     return fig


server = app.server  # 这行加在`app = Dash(__name__)`之后

if __name__ == '__main__':
    app.run(debug=True)
