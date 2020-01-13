"""
Created on Wed Jan  8 20:28:59 2020

@author: karth
"""
import dash
import dash_core_components,dash_html_components,dash.dependencies,datetime,plotly
from dash_core_components import Dropdown,Graph,Slider
print('dash_core_components',dash_core_components.__version__)
from dash_html_components import H3,H6,Div,P,A,Label
print('dash_html_components',dash_html_components.__version__)
from dash.dependencies import Input, Output
# print('dash.dependencies',dash.dependencies.__version__)
# print('datetime',datetime.__version__)

print('dash version - ',dash.__version__)
import pandas as pd
print('pandas version - ',pd.__version__)
import numpy as np
print('numpy version - ',np.__version__)
np.random.seed(0)


# from pandas_datareader import data as web
# print('pandas_datareader - ',pandas_datareader.__version__)

import plotly.express as px
print('plotly = ',plotly.__version__)
import plotly.graph_objects as go


import simpy
print('simpy version: ',simpy.__version__)

# import matplotlib.pyplot as plt
# print('matplotlib',matplotlib.__version__)

# import panel as pn
# print('panel',pn.__version__)
# pn.extension()




external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server



def warehouse_run(env,order_cutoff, order_target):
    global inventory_level,profit,units_ordered
    
    inventory_level = order_target
    profit = 0.0
    units_ordered = 0
    
    #we need an infinite loop
    while True:
        customer_arrival = generate_customer_arrival()
        yield env.timeout(customer_arrival) #wait for the time interval for customer arrival
        profit -= inventory_level*2*customer_arrival
        
        demand = generate_customer_demand()
        #branch-1 : if demand is smaller than inventory, then we can sell complete amount
        if demand < inventory_level:
            profit +=100*demand
            inventory_level -= demand
            print('on {:.2f} day we sold {} and remaining inventory {}'.format(env.now,demand,inventory_level))
        #branch-2: if demand is more than inventory, then sell whatever portion of demand we can satisfy
        else:
            profit += 100*inventory_level
            inventory_level = 0
            print('on {:.2f} day we sold {} (out of stock)'.format(env.now,inventory_level))
    
        if inventory_level < order_cutoff and units_ordered == 0:
            #our inventory levels are below organization's policy level and there are no new orders placed, 
            #in such scenario we need to place an order
            env.process(handle_order(env,order_target))


#process generators
def generate_customer_arrival():
    return np.random.exponential(1.0/5)

#process generators
def generate_customer_demand():
    return np.random.randint(1,5)

def handle_order(env,order_target):
    global inventory_level,profit,units_ordered
    
    
    units_ordered = order_target -inventory_level
    print('on {:.2f} day we placed an order for {}'.format(env.now,units_ordered))
    profit -= 50*units_ordered
    yield env.timeout(2.0)
    inventory_level += units_ordered
    print('on {:.2f} day we received an order for {} and inventory level = {}'.format(env.now,units_ordered,inventory_level))
    units_ordered = 0


def observe(env,observation_time,inventory_level_list):
    global inventory_level
    
    while True:
        observation_time.append(env.now)
        inventory_level_list.append(inventory_level)
        yield env.timeout(0.1) #we will get 10 observations per day

        
def run_simulation(days,cutoff,target):
    observation_time = []
    inventory_level_list = []
    env = simpy.Environment()
    env.process(warehouse_run(env,cutoff,target))
    env.process(observe(env,observation_time,inventory_level_list))
    env.run(until=days)
    inventory_DF = pd.DataFrame({
                            'Time':observation_time,
                            'Inventory_Level':inventory_level_list
    })
    return inventory_DF



# UI layout - DASH app

app.layout = Div([
        
        H3('Inventory Management using Discrete Event Simulation'),
        A('Karthik Anumalasetty- LinkedIn', href="https://www.linkedin.com/in/karthikanumalasetty/", target="_blank"),
        A('Karthik Anumalasetty- GitHub', href="https://www.linkedin.com/in/karthikanumalasetty/", target="_blank"),
       P('Unit Margin = $50 and Lead Time for Purchase Order = 2 days'),
       P('Days to simulate 1 to 30 :'),
       P(id='days-slider-output', style={'margin-top': 20}),
       Slider(
        id='days-slider',
        min=0,
        max=30,
        step=1,
        value=25,
        updatemode='drag'
        ),
       P('Inventory Cutoff level (units 1 to 100) :'),
       Div(id='inv-cutoff-slider-output', style={'margin-top': 20}),
       Slider(
        id='inv-cutoff-slider',
        min=0,
        max=100,
        step=1,
        value=32,
        updatemode='drag'
        ),
       P('Inventory Target level (units 1 to 100)  :'),
       Div(id='inv-target-slider-output', style={'margin-top': 20}),
       Slider(
        id='inv-target-slider',
        min=0,
        max=100,
        step=1,
        value=75,
        updatemode='drag'
        ),
        Graph(id='my-graph')
        ])
        
#Server logic of DASH app

@app.callback(
    [Output('days-slider-output',component_property='children'),
    Output('inv-cutoff-slider-output',component_property='children'),
    Output('inv-target-slider-output',component_property='children'),
    Output('my-graph',component_property='figure')],
    [Input('days-slider',component_property='value'),
     Input('inv-cutoff-slider',component_property='value'),
     Input('inv-target-slider',component_property='value'),
     ])
def update_graph(days_slider,inv_cutoff_slider,inv_target_slider):
    
    print('days_slider',days_slider)
    print('inv_cutoff_slider',inv_cutoff_slider)
    print('inv_target_slider',inv_target_slider)
    
    observation_time = []
    inventory_level_list = []
    
    cutoff = inv_cutoff_slider
    target = inv_target_slider
    days = days_slider
    
    env = simpy.Environment()
    env.process(warehouse_run(env,cutoff,target))
    env.process(observe(env,observation_time,inventory_level_list))
    env.run(until=days)
    inventory_DF = pd.DataFrame({
                            'Time':observation_time,
                            'Inventory_Level':inventory_level_list
                            })
    inventory_DF['cutoff_Level'] = cutoff
    inventory_DF['target_Level'] = target
    inventory_DF['zero_Level'] = 0
    
    # fig = inventory_DF.plot(x='Time', y='Inventory_Level',style='.-',ylim=(0,100),figsize=(10,6)).get_figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=inventory_DF['Time'], y=inventory_DF['Inventory_Level'],mode="lines+markers",showlegend=False,name="Inventory"))
    cutoff_line = go.Scatter(x=inventory_DF['Time'],y=inventory_DF['cutoff_Level'],mode="lines",line=go.scatter.Line(color="red"),showlegend=False,name="Cutoff Inventory")
    target_line = go.Scatter(x=inventory_DF['Time'],y=inventory_DF['target_Level'],mode="lines",line=go.scatter.Line(color="green"),showlegend=False,name="Target Inventory")
    zero_line = go.Scatter(x=inventory_DF['Time'],y=inventory_DF['zero_Level'],mode="lines",line=go.scatter.Line(color="orange"),showlegend=False,name="Zero Inventory")
    fig.add_trace(cutoff_line)
    fig.add_trace(target_line)
    fig.add_trace(zero_line)
    fig.update_layout(title='Inventory Management using Discrete Event Simulation ',
                   xaxis_title='Simulation Time (in days)',
                   yaxis_title='Inventory Level (in units)')
    print('Simulation completed, returning figure')
    return days_slider,inv_cutoff_slider,inv_target_slider,fig



if __name__ == "__main__":
        app.server.run(debug=False)
