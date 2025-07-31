import pandas as pd
import dash
from dash import html, dcc, callback, Output, Input, dash_table, State
import plotly.express as px
from dash.exceptions import PreventUpdate

def get_last_word(text):
    if not isinstance(text, str):
        return ""
    words = text.strip().split()
    return words[-1] if words else ""

debt_grades = ['Незачет', 'Н/я', 'Неуд']

def convert_semester(row):
    """Преобразует семестр из формата 'курс, семестр' в стандартную нумерацию (1-8)"""
    try:
        course = int(row['Курс'])
        semester_in_course = int(row['Семестр'])
        return (course - 1) * 2 + semester_in_course
    except (ValueError, KeyError):
        return row['Семестр']  # Если не получается преобразовать, оставляем как есть
    
# Словарь для перевода текстовых оценок в числа
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

# Загрузка данных
df = pd.read_csv('Компетенции.csv', encoding='cp1251', sep=';')
df_attendance = pd.read_csv('Посещаемость.csv', encoding='cp1251', sep=';')  # Файл с посещаемостью

df_attendance['Семестр'] = df_attendance.apply(convert_semester, axis=1)

# Преобразуем текстовые оценки в числа
df['Числовая_оценка'] = df['Оценка'].map(grade_map)

def calculate_competency_score(competency_group, min_score=False):
    if 'Описание' not in competency_group.columns:
        raise ValueError("Для правильной обработки NULL нужен столбец 'Описание'")
    
    # Исключаем записи с "Не изуч." (6)
    studied_group = competency_group[competency_group['Числовая_оценка'] != 6].copy()
    
    N = len(studied_group)  # Теперь считаем только изученные
    if N == 0:
        return 0
    
    # Разделяем зачеты и экзамены (уже без "Не изуч.")
    credits = studied_group[(studied_group['ДиффенцированныйЗачет'] == 0)]
    exams = studied_group[(studied_group['ДиффенцированныйЗачет'] == 1)]
    
    X = len(credits)  # Количество зачетов
    Y = len(exams)    # Количество экзаменов

    total_score = 0
    
    if X > 0:
        credit_weight = X / N  # Масса зачетов
        per_credit = (credit_weight / X) * 100  # Вклад одного зачета
        
        for _, row in credits.iterrows():
            grade = row['Числовая_оценка']
            if min_score:
                # Минимальный балл - считаем как "зачет"
                total_score += per_credit
            else:
                # Реальный расчет
                if grade == 7:  # Зачет
                    total_score += per_credit
                elif grade == -1:  # Незачет
                    total_score += 0

    if Y > 0:
        exam_weight = Y / N  # Масса экзаменов
        per_exam_max = (exam_weight / Y) * 100  # Макс вклад экзамена
        
        for _, row in exams.iterrows():
            grade = row['Числовая_оценка']
            if min_score:
                # Минимальный балл - считаем как "удовл" (3)
                total_score += 0.5 * per_exam_max
            else:
                # Реальный расчет
                if grade == 3:  # Удовл
                    total_score += 0.5 * per_exam_max
                elif grade == 4:  # Хор
                    total_score += 0.75 * per_exam_max
                elif grade == 5:  # Отл
                    total_score += per_exam_max
    
    return round(total_score, 2)

# Инициализация Dash приложения
app = dash.Dash(__name__)

# Получаем уникальные типы компетенций, семестры и группы для фильтров
competency_types = sorted(df['Тип_Компетенции'].dropna().unique())
semesters = sorted(df['Семестр'].dropna().unique())
groups = sorted(df['Название'].dropna().unique())  # Новый фильтр по группам

# Получаем уникальные значения для фильтров посещаемости
attendance_groups = sorted(df_attendance['Группа'].dropna().unique())
attendance_courses = sorted(df_attendance['Курс'].dropna().unique())
attendance_semesters = sorted(df_attendance['Семестр'].dropna().unique())  # Теперь здесь стандартные семестры 1-8
attendance_teachers = sorted(df_attendance['Преподаватель'].dropna().unique())
attendance_subjects = sorted(df_attendance['Дисциплина'].dropna().unique())
attendance_types = sorted(df_attendance['ВидЗанятий'].dropna().unique())
attendance_codes = sorted(df_attendance['Код'].dropna().unique())

# Получаем уникальные значения для фильтров успеваемости
performance_filters = {
    'Дисциплина': sorted(df['Дисциплина'].dropna().unique()),
    'Курс': sorted(df['Курс'].dropna().unique()),
    'Семестр': sorted(df['Семестр'].dropna().unique()),
    'КодКомпетенции': sorted(df['КодКомпетенции'].dropna().unique()),
    'Компетенция': sorted(df['Компетенция'].dropna().unique()),
    'Тип_Компетенции': sorted(df['Тип_Компетенции'].dropna().unique()),
    'Название': sorted(df['Название'].dropna().unique()),
    'УчебныйГод': sorted(df['УчебныйГод'].dropna().unique()),
    'Код_Студента': sorted(df['Код_Студента'].dropna().unique())
}

# Макет страницы
# Макет страницы
app.layout = html.Div([
    html.Div(className='row', children=[
        html.Div(className='four columns div-user-controls', children=[
            html.H2('График компетенций студентов'),
            html.P('Выберите группу:'),
            dcc.Dropdown(
                id='group-dropdown',
                options=[{'label': group, 'value': group} for group in groups],
                value=groups[0] if groups else None,  # Выбираем первую группу по умолчанию
                multi=False,  
                style={'color': 'black'}
            ),
            html.P('Выберите студента:'),
            dcc.Dropdown(
                id='student-dropdown',
                options=[],  # Будет заполнено через callback
                value=None,
                clearable=False,
                style={'color': 'black'}
            ),
            html.P('Выберите семестр:'),
            dcc.Dropdown(
                id='semester-dropdown',
                options=[{'label': f"Семестр {sem}", 'value': sem} for sem in semesters],
                value=semesters,  # По умолчанию выбраны все семестры
                multi=True,
                style={'color': 'black'}
            ),
            html.P('Выберите тип компетенции:'),
            dcc.Dropdown(
                id='competency-type-dropdown',
                options=[{'label': tp, 'value': tp} for tp in competency_types],
                value=competency_types,  # По умолчанию выбраны все типы
                multi=True,
                style={'color': 'black'}
            ),
            dcc.Checklist(
                id='show-min-score',
                options=[{'label': ' Показать минимальный балл (тройки/зачеты)', 'value': 'show'}],
                value=['show'],
                style={'margin-top': '10px'}
            ),
            html.Div(id='student-grades-info', style={
                'margin-top': '20px',
                'max-height': '400px',
                'overflow-y': 'auto',
                'border': '1px solid #ddd',
                'border-radius': '5px',
                'padding': '10px'
            })
        ]),
        html.Div(className='eight columns div-for-charts bg-grey', children=[
            dcc.Tabs([
                dcc.Tab(label='Компетенции', children=[
                    dcc.Graph(id='radar-chart', style={'height': '70vh'}),
                    html.Div(id='competency-details', style={
                        'margin-top': '20px',
                        'border': '1px solid #ddd',
                        'border-radius': '5px',
                        'padding': '10px',
                        'display': 'none'  # Сначала скрываем
                    })
                ]),
                dcc.Tab(label='Посещаемость и успеваемость', children=[
                    html.Div([
                        dcc.Tabs([
                            dcc.Tab(label='Посещаемость', children=[
                                html.Div([
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Группа:'),
                                            dcc.Dropdown(
                                                id='attendance-group-dropdown',
                                                options=[{'label': group, 'value': group} for group in attendance_groups],
                                                value=attendance_groups,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Код:'),  # New filter for Код
                                            dcc.Dropdown(
                                                id='attendance-code-dropdown',
                                                options=[{'label': code, 'value': code} for code in attendance_codes],
                                                value=attendance_codes,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Курс:'),
                                            dcc.Dropdown(
                                                id='attendance-course-dropdown',
                                                options=[{'label': course, 'value': course} for course in attendance_courses],
                                                value=attendance_courses,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Семестр:'),
                                            dcc.Dropdown(
                                                id='attendance-semester-dropdown',
                                                options=[{'label': semester, 'value': semester} for semester in attendance_semesters],
                                                value=attendance_semesters,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Преподаватель:'),
                                            dcc.Dropdown(
                                                id='attendance-teacher-dropdown',
                                                options=[{'label': teacher, 'value': teacher} for teacher in attendance_teachers],
                                                value=attendance_teachers,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Дисциплина:'),
                                            dcc.Dropdown(
                                                id='attendance-subject-dropdown',
                                                options=[{'label': subject, 'value': subject} for subject in attendance_subjects],
                                                value=attendance_subjects,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Вид занятий:'),
                                            dcc.Dropdown(
                                                id='attendance-type-dropdown',
                                                options=[{'label': type_, 'value': type_} for type_ in attendance_types],
                                                value=attendance_types,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    dcc.Graph(id='attendance-pie-chart', style={'height': '60vh'}),
                                    html.Div(id='attendance-details', style={
                                        'margin-top': '20px',
                                        'border': '1px solid #ddd',
                                        'border-radius': '5px',
                                        'padding': '10px'
                                    })
                                ])
                            ]),
                            dcc.Tab(label='Успеваемость', children=[
                                html.Div([
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Дисциплина:'),
                                            dcc.Dropdown(
                                                id='performance-subject-dropdown',
                                                options=[{'label': subj, 'value': subj} for subj in performance_filters['Дисциплина']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Курс:'),
                                            dcc.Dropdown(
                                                id='performance-course-dropdown',
                                                options=[{'label': course, 'value': course} for course in performance_filters['Курс']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Семестр:'),
                                            dcc.Dropdown(
                                                id='performance-semester-dropdown',
                                                options=[{'label': sem, 'value': sem} for sem in performance_filters['Семестр']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Компетенция:'),
                                            dcc.Dropdown(
                                                id='performance-competency-dropdown',
                                                options=[{'label': comp, 'value': comp} for comp in performance_filters['Компетенция']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Тип компетенции:'),
                                            dcc.Dropdown(
                                                id='performance-competency-type-dropdown',
                                                options=[{'label': tp, 'value': tp} for tp in performance_filters['Тип_Компетенции']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Группа:'),
                                            dcc.Dropdown(
                                                id='performance-group-dropdown',
                                                options=[{'label': group, 'value': group} for group in performance_filters['Название']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div(className='row', children=[
                                        html.Div(className='six columns', children=[
                                            html.P('Учебный год:'),
                                            dcc.Dropdown(
                                                id='performance-year-dropdown',
                                                options=[{'label': year, 'value': year} for year in performance_filters['УчебныйГод']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ]),
                                        html.Div(className='six columns', children=[
                                            html.P('Код студента:'),
                                            dcc.Dropdown(
                                                id='performance-student-dropdown',
                                                options=[{'label': stud, 'value': stud} for stud in performance_filters['Код_Студента']],
                                                value=None,
                                                multi=True,
                                                style={'color': 'black'}
                                            )
                                        ])
                                    ]),
                                    html.Div([
                                        html.Button('Сбросить фильтр по оценке', 
                                                id='reset-grade-filter', 
                                                style={'margin-top': '10px', 'margin-bottom': '10px'})
                                    ]),
                                    dcc.Graph(id='performance-pie-chart', style={'height': '60vh'}),
                                    html.Div(id='performance-details', style={
                                        'margin-top': '20px',
                                        'border': '1px solid #ddd',
                                        'border-radius': '5px',
                                        'padding': '10px'
                                    })
                                ])
                            ])
                        ])
                    ])
                ]),
                # Выносим вкладку "Рейтинги" на верхний уровень
                dcc.Tab(label='Рейтинги', children=[
                    html.Div([
                        html.H3('Рейтинг студентов'),
                        html.Div([
                            html.P('Выберите группу для рейтинга:'),
                            dcc.Dropdown(
                                id='rating-group-dropdown',
                                options=[{'label': group, 'value': group} for group in groups],
                                value=None,
                                multi=False,
                                style={'color': 'black'}
                            ),
                            html.P('Выберите семестр:'),
                            dcc.Dropdown(
                                id='rating-semester-dropdown',
                                options=[{'label': sem, 'value': sem} for sem in semesters],
                                value=None,
                                multi=False,
                                style={'color': 'black'}
                            ),
                            html.Button('Обновить рейтинги', id='update-ratings-button', 
                                    style={'margin-top': '10px'})
                        ], style={'margin-bottom': '20px'}),
                        
                        html.Div(id='ratings-container', children=[
                            dash_table.DataTable(
                                id='ratings-table',
                                style_table={'overflowX': 'auto'},
                                style_cell={
                                    'minWidth': '100px', 'width': '100px', 'maxWidth': '100px',
                                    'whiteSpace': 'normal',
                                    'textAlign': 'center',
                                    'padding': '5px'
                                },
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': 'rgb(248, 248, 248)'
                                    },
                                    {
                                        'if': {'column_id': 'Студент'},
                                        'fontWeight': 'bold',
                                        'textAlign': 'left'
                                    },
                                        # Добавляем выделение строк с долгами
                                    {
                                        'if': {
                                            'filter_query': '{Долги} > 0'
                                        },
                                        'backgroundColor': 'rgba(255, 0, 0, 0.1)',
                                        'border': '1px solid rgba(255, 0, 0, 0.2)'
                                    },
                                    # Ярче выделяем ячейку с количеством долгов
                                    {
                                        'if': {
                                            'column_id': 'Долги',
                                            'filter_query': '{Долги} > 0'
                                        },
                                        'backgroundColor': 'rgba(255, 0, 0, 0.3)',
                                        'fontWeight': 'bold',
                                        'color': 'darkred'
                                    }

                                ],
                                sort_action='native',  # Добавьте эту строку для включения сортировки
                                sort_mode='single'
                            )
                        ])
                    ])
                ])
            ])
        ])
    ])
])


# Функция для расчета рейтингов
def calculate_ratings(selected_group, selected_semester):
    if not selected_group or not selected_semester:
        return pd.DataFrame()
    
    # Создаем копию данных для безопасной модификации
    group_df = df[df['Название'] == selected_group].copy()
    semester_df = group_df[group_df['Семестр'] == selected_semester].copy()
    
    if semester_df.empty:
        return pd.DataFrame()
    
    # Добавляем столбец с последним словом компетенции (используя .loc для избежания предупреждения)
    semester_df.loc[:, 'last_word'] = semester_df['Компетенция'].apply(get_last_word)
    
    student_performance = {}
    for student, student_data in semester_df.groupby('Код_Студента'):
        # Создаем копию данных студента для безопасной работы
        student_data = student_data.copy()
        
        total_score = 0
        competency_count = 0
        
        for last_word, last_word_group in student_data.groupby('last_word'):
            # Исключаем записи с "Не изуч." (6)
            studied_group = last_word_group[last_word_group['Числовая_оценка'] != 6].copy()
            
            if studied_group.empty:
                continue
                
            score = calculate_competency_score(studied_group)
            total_score += score
            competency_count += 1
        
        avg_score_percent = total_score / competency_count if competency_count > 0 else 0
        avg_score_5 = (avg_score_percent / 100) * 5
        
        # Считаем долги (исключая "Не изуч.")
        debts_df = student_data[
            (student_data['Оценка'].isin(['Незачет', 'Н/я', 'Неуд'])) & 
            (student_data['Числовая_оценка'] != 6)
        ].copy()
        
        student_performance[student] = {
            'avg_score_percent': avg_score_percent,
            'avg_score_5': avg_score_5,
            'debts': len(debts_df)
        }
    
    # Рассчитываем посещаемость для каждого студента
    student_attendance = {}
    attendance_group_df = df_attendance[(df_attendance['Группа'] == selected_group) & 
                                       (df_attendance['Семестр'] == selected_semester)]
    
    for student in student_performance.keys():
        student_attendance_df = attendance_group_df[attendance_group_df['Код'] == student]
        
        if not student_attendance_df.empty:
            total_classes = student_attendance_df['ВсегоЗанятийПоЖурналу'].sum()
            missed_classes = student_attendance_df['ПропусковНеуважитПрич'].sum()
            attendance_percent = ((total_classes - missed_classes) / total_classes * 100 
                                 if total_classes > 0 else 100)
        else:
            attendance_percent = 0
            
        student_attendance[student] = attendance_percent
    
    # Создаем DataFrame с рейтингами
    ratings_data = []
    for student in student_performance.keys():
        ratings_data.append({
            'Студент': f"Студент {student}",
            'Успеваемость (%)': round(student_performance[student]['avg_score_percent'], 2),
            'Успеваемость (5-балльная)': round(student_performance[student]['avg_score_5'], 2),
            'Долги': student_performance[student]['debts'],
            'Посещаемость (%)': round(student_attendance.get(student, 100), 2)
        })
    
    ratings_df = pd.DataFrame(ratings_data)
    
    # Рассчитываем рейтинги (используем 5-балльную шкалу для сортировки)
    if not ratings_df.empty:
        # Рейтинг по успеваемости (чем выше балл, тем выше рейтинг)
        ratings_df['Рейтинг в группе (успеваемость)'] = ratings_df['Успеваемость (5-балльная)'].rank(ascending=False, method='dense').astype(int)
        
        # Рейтинг по посещаемости (чем выше %, тем выше рейтинг)
        ratings_df['Рейтинг в группе (посещаемость)'] = ratings_df['Посещаемость (%)'].rank(ascending=False, method='dense').astype(int)
        
        # Для рейтинга на направлении, курсе и в институте - в реальном приложении 
        # нужно было бы иметь данные по всем группам, здесь просто заполняем теми же значениями
        ratings_df['Рейтинг на направлении (успеваемость)'] = ratings_df['Рейтинг в группе (успеваемость)']
        ratings_df['Рейтинг на направлении (посещаемость)'] = ratings_df['Рейтинг в группе (посещаемость)']
        ratings_df['Рейтинг на курсе (успеваемость)'] = ratings_df['Рейтинг в группе (успеваемость)']
        ratings_df['Рейтинг на курсе (посещаемость)'] = ratings_df['Рейтинг в группе (посещаемость)']
        ratings_df['Рейтинг в институте (успеваемость)'] = ratings_df['Рейтинг в группе (успеваемость)']
        ratings_df['Рейтинг в институте (посещаемость)'] = ratings_df['Рейтинг в группе (посещаемость)']
    
    return ratings_df

# Callback для обновления рейтинговой таблицы
@app.callback(
    Output('ratings-table', 'data'),
    Output('ratings-table', 'columns'),
    Input('update-ratings-button', 'n_clicks'),
    State('rating-group-dropdown', 'value'),
    State('rating-semester-dropdown', 'value')
)
def update_ratings_table(n_clicks, selected_group, selected_semester):
    if n_clicks is None or not selected_group or not selected_semester:
        raise PreventUpdate
    
    ratings_df = calculate_ratings(selected_group, selected_semester)
    
    if ratings_df.empty:
        return [], []
    
    # Формируем колонки для таблицы
    columns = [
        {'name': 'Студент', 'id': 'Студент'},
        {'name': 'Успеваемость (%)', 'id': 'Успеваемость (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        {'name': 'Успеваемость (5-балльная)', 'id': 'Успеваемость (5-балльная)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        {'name': 'Долги', 'id': 'Долги', 'type': 'numeric'},
        {'name': 'Посещаемость (%)', 'id': 'Посещаемость (%)', 'type': 'numeric', 'format': {'specifier': '.2f'}},
        {'name': 'Рейтинг в группе (успеваемость)', 'id': 'Рейтинг в группе (успеваемость)', 'type': 'numeric'},
        {'name': 'Рейтинг в группе (посещаемость)', 'id': 'Рейтинг в группе (посещаемость)', 'type': 'numeric'},
        {'name': 'Рейтинг на направлении (успеваемость)', 'id': 'Рейтинг на направлении (успеваемость)', 'type': 'numeric'},
        {'name': 'Рейтинг на направлении (посещаемость)', 'id': 'Рейтинг на направлении (посещаемость)', 'type': 'numeric'},
        {'name': 'Рейтинг на курсе (успеваемость)', 'id': 'Рейтинг на курсе (успеваемость)', 'type': 'numeric'},
        {'name': 'Рейтинг на курсе (посещаемость)', 'id': 'Рейтинг на курсе (посещаемость)', 'type': 'numeric'},
        {'name': 'Рейтинг в институте (успеваемость)', 'id': 'Рейтинг в институте (успеваемость)', 'type': 'numeric'},
        {'name': 'Рейтинг в институте (посещаемость)', 'id': 'Рейтинг в институте (посещаемость)', 'type': 'numeric'}
    ]
    
    return ratings_df.to_dict('records'), columns

# Callback для обновления списка студентов при выборе группы
@app.callback(
    Output('student-dropdown', 'options'),
    Output('student-dropdown', 'value'),
    Input('group-dropdown', 'value')  
)
def update_student_dropdown(selected_group):
    if not selected_group:
        return [], None
    
    filtered_df = df[df['Название'] == selected_group]  # Фильтруем по одной группе
    unique_students = filtered_df['Код_Студента'].unique()
    
    options = [{'label': f"Студент {student}", 'value': student} for student in unique_students]
    
    # Выбираем первого студента в списке, если есть
    value = unique_students[0] if len(unique_students) > 0 else None
    
    return options, value

# Callback для обновления графика и основной информации
@app.callback(
    [Output('radar-chart', 'figure'),
     Output('student-grades-info', 'children'),
     Output('competency-details', 'style'),
     Output('competency-details', 'children')],
    [Input('student-dropdown', 'value'),
     Input('semester-dropdown', 'value'),
     Input('competency-type-dropdown', 'value'),
     Input('show-min-score', 'value'),
     Input('radar-chart', 'clickData'),
     Input('group-dropdown', 'value')],  
    [State('competency-details', 'style')]
)
def update_dashboard(selected_student, selected_semesters, selected_types, show_min, click_data, selected_group, details_style):
    def get_last_word(text):
        if not isinstance(text, str):
            return ""
        words = text.strip().split()
        return words[-1] if words else ""
    
    def extract_year(year_str):
        try:
            return int(year_str.split('-')[0])
        except:
            return 0
    
    if not selected_student or not selected_group:
        return px.line_polar(), html.P("Выберите группу и студента"), {'display': 'none'}, None
    
    # Получаем все данные для студента
    filtered_df = df[(df['Код_Студента'] == selected_student) & 
                   (df['Семестр'].isin(selected_semesters)) &
                   (df['Тип_Компетенции'].isin(selected_types)) &
                   (df['Название'] == selected_group)].copy()
    
    if filtered_df.empty:
        return px.line_polar(), html.P("Нет данных для выбранных критериев"), {'display': 'none'}, None
    
    # Добавляем столбец с последним словом компетенции
    filtered_df['last_word'] = filtered_df['Компетенция'].apply(get_last_word)
    filtered_df['year_num'] = filtered_df['УчебныйГод'].apply(extract_year)
    
    # Находим последние версии каждой компетенции (по последнему слову)
    latest_versions = {}
    for _, row in filtered_df.iterrows():
        last_word = row['last_word']
        year = row['year_num']
        if last_word not in latest_versions or year > latest_versions[last_word]['year']:
            latest_versions[last_word] = {
                'competency': row['Компетенция'],
                'year': year
            }
    
    # Создаем маппинг всех компетенций к их последней версии
    competency_mapping = {}
    for comp in filtered_df['Компетенция'].unique():
        last_word = get_last_word(comp)
        if last_word in latest_versions:
            competency_mapping[comp] = latest_versions[last_word]['competency']
    
    # Для расчета баллов группируем по последнему слову (объединяем все версии)
    competency_scores = []
    min_competency_scores = []
    competency_types_dict = {}
    competency_studied = {}

    for last_word, group in filtered_df.groupby('last_word'):
        # Исключаем из группы записи с "Не изуч."
        studied_group = group[group['Числовая_оценка'] != 6]
        
        if studied_group.empty:
            # Все записи этой группы имеют "Не изуч."
            continue
            
        latest_comp = latest_versions.get(last_word, {}).get('competency', group['Компетенция'].iloc[0])
        competency_types_dict[last_word] = studied_group['Тип_Компетенции'].iloc[0]
        
        score = calculate_competency_score(studied_group)
        competency_scores.append({
            'Компетенция': latest_comp,
            'last_word': last_word,
            'Балл': score,
        })
        
        if 'show' in show_min:
            min_score = calculate_competency_score(group, min_score=True)
            min_competency_scores.append({
                'Компетенция': latest_comp,
                'last_word': last_word,
                'Балл': min_score,
            })
    
    if not competency_scores:
        return px.line_polar(), html.P("Все компетенции не изучены для выбранных семестров"), {'display': 'none'}, None
    
    # Создаем DataFrame для графика
    result_df = pd.DataFrame(competency_scores)
    result_df['Тип_Компетенции'] = result_df['last_word'].map(competency_types_dict)
    
    # Создаем radar chart
    fig = px.line_polar(
        result_df,
        r='Балл',
        theta='last_word',
        line_close=True,
        title=f'Компетенции студента {selected_student} (Группа: {selected_group})',
        template='plotly_white',
        hover_data={'Тип_Компетенции': True, 'Компетенция': True}
    )
    
    # Добавляем минимальный балл если нужно
    if 'show' in show_min and min_competency_scores:
        min_df = pd.DataFrame(min_competency_scores)
        min_df['Тип_Компетенции'] = min_df['last_word'].map(competency_types_dict)
        
        fig.add_trace(px.line_polar(
            min_df,
            r='Балл',
            theta='last_word',
            line_close=True
        ).data[0])
        
        fig.data[1].update(
            line=dict(color='red', width=1, dash='dot'),
            fill='none',
            name='Минимальный балл',
            hovertemplate='<b>Компетенция: %{theta}</b><br>Балл: %{r:.2f}%<br><extra></extra>'
        )
    
    # Настройка графика
    fig.data[0].update(
        fill='toself',
        mode='lines+markers',
        line=dict(width=2, color='blue'),
        marker=dict(size=5, color='blue'),
        fillcolor='rgba(0, 100, 255, 0.3)',
        name='Фактический балл',
        hovertemplate='<b>%{customdata[1]}</b><br>Балл: %{r:.2f}%<br>Тип: %{customdata[0]}<extra></extra>'
    )
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[0, 20, 40, 60, 80, 100],
                ticktext=['0%', '20%', '40%', '60%', '80%', '100%']
            ),
            angularaxis=dict(
                rotation=90
            )
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        showlegend=True
    )
    
    # Таблица со всеми оценками
    # Таблица со всеми оценками (добавляем колонку с типом зачета)
    grades_table = dash_table.DataTable(
        id='grades-table',
        columns=[
            {'name': 'Дисциплина', 'id': 'Дисциплина'},
            {'name': 'Оценка', 'id': 'Оценка'},
            {'name': 'Тип зачета', 'id': 'Тип_зачета'},  # Новая колонка
            {'name': 'Семестр', 'id': 'Семестр'},
            {'name': 'Тип', 'id': 'Тип_Компетенции'},
            {'name': 'Компетенция', 'id': 'Компетенция'},
            {'name': 'Группа', 'id': 'Название'}
        ],
        data=[{
            'Дисциплина': row['Дисциплина'],
            'Оценка': row['Оценка'],
            'Тип_зачета': 'Дифф. зачет' if row['ДиффенцированныйЗачет'] == 1 else 'Зачет',
            'Семестр': row['Семестр'],
            'Тип_Компетенции': row['Тип_Компетенции'],
            'Компетенция': row['Компетенция'],
            'Название': row['Название']
        } for _, row in filtered_df.iterrows()],
        style_table={'maxHeight': '350px', 'overflowY': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{Оценка} = "Незачет" || {Оценка} = "Н/я" || {Оценка} = "Неуд"',
                'column_id': 'Оценка'},
            'backgroundColor': 'rgba(255, 0, 0, 0.3)',
            'fontWeight': 'bold',
            'color': 'darkred'}

        ],
        page_size=10
    )
        
    # Обработка клика - показываем все оценки по всем версиям этой компетенции
    if click_data:
        clicked_last_word = click_data['points'][0]['theta']
        
        # Находим все компетенции с этим последним словом
        related_comps = [comp for comp in filtered_df['Компетенция'].unique() 
                        if get_last_word(comp) == clicked_last_word]
        
        # Фильтруем данные по всем связанным компетенциям
        comp_df = filtered_df[filtered_df['Компетенция'].isin(related_comps)]
        
        if not comp_df.empty:
            available_columns = ['Дисциплина', 'Оценка', 'Семестр', 'Тип_Компетенции', 'Название']
            if 'ДиффенцированныйЗачет' in comp_df.columns:
                available_columns.append('ДиффенцированныйЗачет')
            
            details_table = dash_table.DataTable(
                columns=[{'name': col, 'id': col} for col in available_columns],
                data=comp_df[available_columns].to_dict('records'),
                style_table={'maxHeight': '300px', 'overflowY': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
                    {'if': {'filter_query': '{Оценка} = "Незачет" || {Оценка} = "Н/я" || {Оценка} = "Неуд"',
                           'column_id': 'Оценка'},
                     'backgroundColor': 'rgba(255, 0, 0, 0.3)',
                     'fontWeight': 'bold',
                     'color': 'darkred'
                     }
                ]
            )
            
            details_content = html.Div([
                html.H4(f'Детали по компетенции: {clicked_last_word}'),
                html.P(f'Тип: {comp_df["Тип_Компетенции"].iloc[0]}'),
                html.P(f'Все версии: {", ".join(related_comps)}'),
                details_table
            ])
            
            return fig, grades_table, {'display': 'block'}, details_content
    
    return fig, grades_table, {'display': 'none'}, None

# Callback для обновления круговой диаграммы посещаемости
@app.callback(
    [Output('attendance-pie-chart', 'figure'),
     Output('attendance-details', 'children'),
     Output('attendance-subject-dropdown', 'options')],  # Добавляем вывод для обновления вариантов дисциплин
    [Input('attendance-group-dropdown', 'value'),
     Input('attendance-code-dropdown', 'value'),
     Input('attendance-course-dropdown', 'value'),
     Input('attendance-semester-dropdown', 'value'),
     Input('attendance-teacher-dropdown', 'value'),
     Input('attendance-subject-dropdown', 'value'),
     Input('attendance-type-dropdown', 'value')],
    [State('attendance-subject-dropdown', 'options')]  # Состояние текущих вариантов дисциплин
)
def update_attendance_chart(selected_groups, selected_codes, selected_courses, selected_semesters, 
                           selected_teachers, selected_subjects, selected_types, current_subject_options):
    # Сначала обновляем варианты дисциплин на основе выбранных преподавателей
    if selected_teachers is None or len(selected_teachers) == 0:
        # Если преподаватели не выбраны, показываем все дисциплины
        subject_options = [{'label': subj, 'value': subj} for subj in attendance_subjects]
    else:
        # Фильтруем дисциплины по выбранным преподавателям
        filtered_subjects = df_attendance[df_attendance['Преподаватель'].isin(selected_teachers)]
        unique_subjects = sorted(filtered_subjects['Дисциплина'].dropna().unique())
        subject_options = [{'label': subj, 'value': subj} for subj in unique_subjects]
    
    # Проверяем, нужно ли обновлять выбранные значения дисциплин
    if selected_subjects is not None:
        # Оставляем только те выбранные дисциплины, которые есть в новых вариантах
        valid_subjects = [subj for subj in selected_subjects 
                         if subj in [opt['value'] for opt in subject_options]]
        if len(valid_subjects) < len(selected_subjects):
            selected_subjects = valid_subjects if len(valid_subjects) > 0 else None
    
    # Если нет выбранных параметров, прерываем обновление графика
    if not all([selected_groups, selected_codes, selected_courses, selected_semesters, 
                selected_teachers, selected_subjects, selected_types]):
        # Возвращаем пустую диаграмму, сообщение и обновленные варианты дисциплин
        return px.pie(), html.P("Выберите параметры для отображения данных"), subject_options
    
    # Фильтруем данные по выбранным параметрам, включая код
    filtered_df = df_attendance[
        (df_attendance['Группа'].isin(selected_groups)) &
        (df_attendance['Код'].isin(selected_codes)) &
        (df_attendance['Курс'].isin(selected_courses)) &
        (df_attendance['Семестр'].isin(selected_semesters)) &
        (df_attendance['Преподаватель'].isin(selected_teachers)) &
        (df_attendance['Дисциплина'].isin(selected_subjects)) &
        (df_attendance['ВидЗанятий'].isin(selected_types))
    ]
    
    if filtered_df.empty:
        return px.pie(), html.P("Нет данных для выбранных критериев"), subject_options
    
    # Агрегируем данные по пропускам
    total_classes = filtered_df['ВсегоЗанятийПоЖурналу'].sum()
    total_absences = filtered_df['ПропусковНеуважитПрич'].sum()
    attended_classes = total_classes - total_absences
    
    # Создаем DataFrame для диаграммы
    pie_data = pd.DataFrame({
        'Тип': ['Посещенные занятия', 'Пропуски по неуважительной причине'],
        'Количество': [attended_classes, total_absences]
    })
    
    # Создаем круговую диаграмму
    fig = px.pie(
        pie_data,
        values='Количество',
        names='Тип',
        title='Посещаемость занятий',
        color='Тип',
        color_discrete_map={
            'Посещенные занятия': 'green',
            'Пропуски по неуважительной причине': 'red'
        },
        hole=0.3
    )
    
    fig.update_traces(
        textinfo='percent+value',
        hoverinfo='label+percent+value',
        marker=dict(line=dict(color='#000000', width=1)))
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Создаем таблицу с деталями посещаемости
    details_table = dash_table.DataTable(
        columns=[
            {'name': 'Группа', 'id': 'Группа'},
            {'name': 'Дисциплина', 'id': 'Дисциплина'},
            {'name': 'Вид занятий', 'id': 'ВидЗанятий'},
            {'name': 'Всего занятий', 'id': 'ВсегоЗанятийПоЖурналу'},
            {'name': 'Пропуски', 'id': 'ПропусковНеуважитПрич'},
            {'name': 'Преподаватель', 'id': 'Преподаватель'},
            {'name': 'Код', 'id': 'Код'}
        ],
        data=filtered_df.to_dict('records'),
        style_table={
            'maxHeight': '300px',
            'overflowY': 'auto',
            'width': '100%'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '5px',
            'fontSize': '12px',
            'fontFamily': 'Arial'
        },
        style_header={
            'backgroundColor': '#f8f9fa',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
    )
    
    details_content = html.Div([
        html.H4('Детали посещаемости'),
        html.P(f'Всего занятий: {total_classes}'),
        html.P(f'Пропущено по неуважительной причине: {total_absences} ({round(total_absences/total_classes*100, 2)}%)'),
        details_table
    ])
    
    return fig, details_content, subject_options

# Callback для обновления фильтров успеваемости
@app.callback(
    [Output('performance-course-dropdown', 'options'),
     Output('performance-semester-dropdown', 'options'),
     Output('performance-competency-dropdown', 'options'),
     Output('performance-competency-type-dropdown', 'options'),
     Output('performance-group-dropdown', 'options'),
     Output('performance-year-dropdown', 'options'),
     Output('performance-student-dropdown', 'options')],
    [Input('performance-subject-dropdown', 'value'),
     Input('performance-course-dropdown', 'value'),
     Input('performance-semester-dropdown', 'value'),
     Input('performance-competency-dropdown', 'value'),
     Input('performance-competency-type-dropdown', 'value'),
     Input('performance-group-dropdown', 'value'),
     Input('performance-year-dropdown', 'value'),
     Input('performance-pie-chart', 'clickData')]  # <<< Добавлен clickData
)
def update_performance_filters(selected_subjects, selected_courses, selected_semesters, 
                             selected_competencies, selected_competency_types, 
                             selected_groups, selected_years, click_data):  # <<< Добавлен click_data
    # Фильтруем данные по выбранным параметрам (каскадное обновление)
    filtered_df = df.copy()
    # Применяем фильтры последовательно
    if selected_subjects:
        filtered_df = filtered_df[filtered_df['Дисциплина'].isin(selected_subjects)]
    if selected_courses:
        filtered_df = filtered_df[filtered_df['Курс'].isin(selected_courses)]
    if selected_semesters:
        filtered_df = filtered_df[filtered_df['Семестр'].isin(selected_semesters)]
    if selected_competencies:
        filtered_df = filtered_df[filtered_df['Компетенция'].isin(selected_competencies)]
    if selected_competency_types:
        filtered_df = filtered_df[filtered_df['Тип_Компетенции'].isin(selected_competency_types)]
    if selected_groups:
        filtered_df = filtered_df[filtered_df['Название'].isin(selected_groups)]
    if selected_years:
        filtered_df = filtered_df[filtered_df['УчебныйГод'].isin(selected_years)]

    # Получаем доступные значения
    available_courses = sorted(filtered_df['Курс'].dropna().unique())
    available_semesters = sorted(filtered_df['Семестр'].dropna().unique())
    available_competencies = sorted(filtered_df['Компетенция'].dropna().unique())
    available_competency_types = sorted(filtered_df['Тип_Компетенции'].dropna().unique())
    available_groups = sorted(filtered_df['Название'].dropna().unique())
    available_years = sorted(filtered_df['УчебныйГод'].dropna().unique())
    available_students = sorted(filtered_df['Код_Студента'].dropna().unique())

    course_options = [{'label': course, 'value': course} for course in available_courses]
    semester_options = [{'label': sem, 'value': sem} for sem in available_semesters]
    competency_options = [{'label': comp, 'value': comp} for comp in available_competencies]
    competency_type_options = [{'label': tp, 'value': tp} for tp in available_competency_types]
    group_options = [{'label': group, 'value': group} for group in available_groups]
    year_options = [{'label': year, 'value': year} for year in available_years]
    student_options = [{'label': f"Студент {stud}", 'value': stud} for stud in available_students]

    return (
        course_options,
        semester_options,
        competency_options,
        competency_type_options,
        group_options,
        year_options,
        student_options
    )

# Callback для сброса значений фильтров при изменении родительских фильтров
@app.callback(
    [Output('performance-course-dropdown', 'value'),
     Output('performance-semester-dropdown', 'value'),
     Output('performance-competency-dropdown', 'value'),
     Output('performance-competency-type-dropdown', 'value'),
     Output('performance-group-dropdown', 'value'),
     Output('performance-year-dropdown', 'value'),
     Output('performance-student-dropdown', 'value')],
    [Input('performance-subject-dropdown', 'value'),
     Input('performance-course-dropdown', 'options'),
     Input('performance-semester-dropdown', 'options'),
     Input('performance-competency-dropdown', 'options'),
     Input('performance-competency-type-dropdown', 'options'),
     Input('performance-group-dropdown', 'options'),
     Input('performance-year-dropdown', 'options')],
    [State('performance-course-dropdown', 'value'),
     State('performance-semester-dropdown', 'value'),
     State('performance-competency-dropdown', 'value'),
     State('performance-competency-type-dropdown', 'value'),
     State('performance-group-dropdown', 'value'),
     State('performance-year-dropdown', 'value'),
     State('performance-student-dropdown', 'value')]
)
def reset_dependent_filters(selected_subjects, course_options, semester_options, 
                          competency_options, competency_type_options, 
                          group_options, year_options,
                          current_courses, current_semesters, current_competencies,
                          current_competency_types, current_groups, current_years,
                          current_students):
    # Определяем, какой фильтр вызвал обновление
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Если изменился фильтр дисциплин, сбрасываем все зависимые фильтры
    if trigger_id == 'performance-subject-dropdown':
        return None, None, None, None, None, None, None
    
    # Проверяем и корректируем значения фильтров, чтобы они соответствовали доступным вариантам
    def filter_values(current_values, available_options):
        if not current_values:
            return None
        available_values = [opt['value'] for opt in available_options]
        filtered_values = [val for val in current_values if val in available_values]
        return filtered_values if filtered_values else None
    
    current_courses = filter_values(current_courses, course_options)
    current_semesters = filter_values(current_semesters, semester_options)
    current_competencies = filter_values(current_competencies, competency_options)
    current_competency_types = filter_values(current_competency_types, competency_type_options)
    current_groups = filter_values(current_groups, group_options)
    current_years = filter_values(current_years, year_options)
    
    return (current_courses, current_semesters, current_competencies,
            current_competency_types, current_groups, current_years, current_students)

# Callback для обновления круговой диаграммы успеваемости (с поддержкой клика)
@app.callback(
    [Output('performance-pie-chart', 'figure'),
     Output('performance-details', 'children'),
     Output('performance-pie-chart', 'clickData')],
    [Input('performance-subject-dropdown', 'value'),
     Input('performance-course-dropdown', 'value'),
     Input('performance-semester-dropdown', 'value'),
     Input('performance-competency-dropdown', 'value'),
     Input('performance-competency-type-dropdown', 'value'),
     Input('performance-group-dropdown', 'value'),
     Input('performance-year-dropdown', 'value'),
     Input('performance-student-dropdown', 'value'),
     Input('performance-pie-chart', 'clickData'),
     Input('reset-grade-filter', 'n_clicks')],
    [State('performance-pie-chart', 'figure'),
     State('performance-pie-chart', 'clickData')]
)
def update_performance_chart(selected_subjects, selected_courses, selected_semesters, 
                           selected_competencies, selected_competency_types, 
                           selected_groups, selected_years, selected_students, 
                           click_data, reset_clicks, current_figure, current_click_data):
    # Определяем, что вызвало callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Если нажата кнопка сброса, очищаем click_data
    if trigger_id == 'reset-grade-filter':
        click_data = None
    
    # Фильтруем данные по выбранным параметрам
    filtered_df = df.copy()
    if selected_subjects:
        filtered_df = filtered_df[filtered_df['Дисциплина'].isin(selected_subjects)]
    if selected_courses:
        filtered_df = filtered_df[filtered_df['Курс'].isin(selected_courses)]
    if selected_semesters:
        filtered_df = filtered_df[filtered_df['Семестр'].isin(selected_semesters)]
    if selected_competencies:
        filtered_df = filtered_df[filtered_df['Компетенция'].isin(selected_competencies)]
    if selected_competency_types:
        filtered_df = filtered_df[filtered_df['Тип_Компетенции'].isin(selected_competency_types)]
    if selected_groups:
        filtered_df = filtered_df[filtered_df['Название'].isin(selected_groups)]
    if selected_years:
        filtered_df = filtered_df[filtered_df['УчебныйГод'].isin(selected_years)]
    if selected_students:
        filtered_df = filtered_df[filtered_df['Код_Студента'].isin(selected_students)]

    if filtered_df.empty:
        return px.pie(), html.P("Нет данных для выбранных критериев"), None

    # Определяем долги (Незачет, Н/я, Неуд)
    debts = ['Незачет', 'Н/я', 'Неуд']
    filtered_df['Долг'] = filtered_df['Оценка'].isin(debts)
    
    # Создаем DataFrame для диаграммы (всегда полные данные, без фильтрации по клику)
    grade_counts = filtered_df['Оценка'].value_counts().reset_index()
    grade_counts.columns = ['Оценка', 'Количество']
    grade_counts['Долг'] = grade_counts['Оценка'].isin(debts)

    # Создаем круговую диаграмму с выделением долгов
    fig = px.pie(
        grade_counts,
        values='Количество',
        names='Оценка',
        title='Распределение оценок',
        hole=0.3
    )
    
    fig.update_traces(
        textinfo='percent+value',
        hoverinfo='label+percent+value',
        marker=dict(line=dict(color='#000000', width=1)))
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Фильтруем данные для таблицы в зависимости от клика
    if click_data and trigger_id != 'reset-grade-filter':
        try:
            clicked_grade = click_data['points'][0]['label']
            table_df = filtered_df[filtered_df['Оценка'] == clicked_grade]
            details_title = f'Детали успеваемости: {clicked_grade}'
        except Exception as e:
            print(f"Ошибка при обработке clickData: {e}")
            table_df = filtered_df
            details_title = 'Детали успеваемости'
    else:
        table_df = filtered_df
        details_title = 'Детали успеваемости'

    # Фильтруем долги для отдельного отображения
    debts_df = table_df[table_df['Долг']]
    
    # Таблица с деталями
    details_table = dash_table.DataTable(
        columns=[
            {'name': 'Студент', 'id': 'Код_Студента'},
            {'name': 'Дисциплина', 'id': 'Дисциплина'},
            {'name': 'Оценка', 'id': 'Оценка'},
            {'name': 'Семестр', 'id': 'Семестр'},
            {'name': 'Компетенция', 'id': 'Компетенция'},
            {'name': 'Группа', 'id': 'Название'},
            {'name': 'Учебный год', 'id': 'УчебныйГод'}
        ],
        data=table_df.to_dict('records'),
        style_table={'overflowY': 'auto', 'maxHeight': '300px'},
        style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '12px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            },
            # Выделяем строки с долгами красным цветом
            {
                'if': {
                    'filter_query': '{Оценка} = "Незачет" || {Оценка} = "Н/я" || {Оценка} = "Неуд"'
                },
                'backgroundColor': 'rgba(255, 0, 0, 0.2)',
                'fontWeight': 'bold',
                'border': '1px solid rgba(255, 0, 0, 0.3)'
            },
            # Ярче выделяем ячейку с оценкой
            {
                'if': {
                    'filter_query': '{Оценка} = "Незачет" || {Оценка} = "Н/я" || {Оценка} = "Неуд"',
                    'column_id': 'Оценка'
                },
                'backgroundColor': 'rgba(255, 0, 0, 0.3)',
                'color': 'darkred'
            }
        ]
    )
    
    # Создаем отдельную таблицу для долгов
    debts_table = dash_table.DataTable(
        columns=[
            {'name': 'Студент', 'id': 'Код_Студента'},
            {'name': 'Дисциплина', 'id': 'Дисциплина'},
            {'name': 'Оценка', 'id': 'Оценка'},
            {'name': 'Семестр', 'id': 'Семестр'},
            {'name': 'Компетенция', 'id': 'Компетенция'},
            {'name': 'Группа', 'id': 'Название'},
            {'name': 'Учебный год', 'id': 'УчебныйГод'}
        ],
        data=debts_df.to_dict('records'),
        style_table={'overflowY': 'auto', 'maxHeight': '300px'},
        style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '12px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgba(255, 0, 0, 0.1)'
            },
            {
                'if': {'row_index': 'even'},
                'backgroundColor': 'rgba(255, 0, 0, 0.05)'
            }
        ]
    )
    
    details_content_children = [
        html.H4(details_title),
        html.P(f'Всего записей: {len(table_df)}')
    ]

    # Добавляем информацию о долгах только если они есть
    if not debts_df.empty:
        details_content_children.extend([
            html.P(f'Количество долгов: {len(debts_df)}', style={'color': 'red', 'fontWeight': 'bold'}),
            html.H5('Все оценки:'),
            details_table,
            html.H5('Долги:', style={'color': 'red', 'marginTop': '20px'}),
            debts_table
        ])
    else:
        details_content_children.extend([
            html.P("Нет долгов", style={'color': 'green', 'fontWeight': 'bold'}),
            html.H5('Все оценки:'),
            details_table
        ])

    details_content = html.Div(details_content_children)
    # Возвращаем:
    # 1. Фигуру (всегда неизменную, даже при клике)
    # 2. Обновленное содержимое таблицы
    # 3. Состояние clickData (None если была нажата кнопка сброса)
    return (
        dash.no_update if trigger_id == 'performance-pie-chart' else fig,  # Не обновляем диаграмму при клике
        details_content,
        None if trigger_id == 'reset-grade-filter' else dash.no_update
    )
# Запуск приложения
if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8050)