#В коде 4 ошибки, которые скорее предупреждения, запуску не мешают
import pandas as pd
import dash
from dash import html, dcc, callback, Output, Input
import plotly.express as px

# Словарь для перевода текстовых оценок в числа(из таблиц Кротовой)
grade_map = {
    'Незачет': -1,
    'NULL': 0,
    'Н/я': 1,
    'Неуд': 2,
    'Удовл': 3,
    'Хор': 4,
    'Отл': 5,
    'Не изуч.': 6,
    'Зачет': 7,
}


df = pd.read_csv('data.csv', encoding='cp1251', sep=';')



# Преобразуем текстовые оценки в числа
df['Оценка'] = df['Оценка'].map(grade_map)

#Есть подозрение что здесь какой-то косяк,за счет того что все данные по каждой компетенции через среднее
#без среднего значения если, то у меня ругался,поэтому должно оно как-то переситываться,но мб не через среднее
df_pivot = df.pivot_table(
    index='Код_Студента',
    columns='Тип_Компетенции',
    values='Оценка',
    aggfunc='mean'
).reset_index()


app = dash.Dash(__name__)

# Макет страницы
app.layout = html.Div([
    html.Div(className='row', children=[
        html.Div(className='four columns div-user-controls', children=[
            html.H2('График компетенций'),
            html.P('Выберите студента:'),
            dcc.Dropdown(
                id='student-dropdown',
                options=[{'label': student, 'value': student}
                         for student in df_pivot['Код_Студента'].unique()],
                value=df_pivot['Код_Студента'].unique()[0],
                clearable=False
            )
        ]),
        html.Div(className='eight columns div-for-charts bg-grey', children=[
            dcc.Graph(id='radar-chart')
        ])
    ])
])

# хз зачем эти 2 строки, дядька в ютубе сказал что надо
@app.callback(
    Output('radar-chart', 'figure'),
    Input('student-dropdown', 'value')
)
def update_radar_chart(selected_student):
    # Фильтруем данные по студенту
    student_data = df_pivot[df_pivot['Код_Студента'] == selected_student]

    # Получаем оценки и типы компетенций
    r_values = student_data.iloc[0, 1:].values
    theta_labels = student_data.columns[1:]

    # Создаём график 
    fig = px.line_polar(
        r=r_values,
        theta=theta_labels,
        line_close=True,
        title=f'Компетенции студента {selected_student}',
        template='plotly_dark'
    )

    # Настройка внешнего вида
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5]  # Оценки от 0 до 5
            ),
            angularaxis=dict(
                direction='clockwise'
            )
        ),
        font_color='white',
        title_font_color='white',
        plot_bgcolor='rgba(0, 0, 0, 0.3)',
        paper_bgcolor='rgba(0, 0, 0, 0)'
    )

    return fig

#Эти строки не трогай.Ютуб и всё остальное предлагает другую запись запуска, но то старые версии и оно не запустится
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050)