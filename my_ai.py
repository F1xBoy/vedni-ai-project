import os
from flask import Flask, request, jsonify
import wikipediaapi
import requests

app = Flask(__name__)

# Инициализируем Википедию
wiki = wikipediaapi.Wikipedia('MyAIWebBot/1.0 (contact@example.com)', 'ru')

# Находим корень проекта, чтобы Vercel не терял HTML и CSS файлы
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def home():
    html_path = os.path.join(BASE_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/style.css')
def css():
    css_path = os.path.join(BASE_DIR, 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/css'}

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '')
    web_search = data.get('web_search', False)

    if not question:
        return jsonify({'answer': 'Введите ваш вопрос!'})

    # Достаем API ключ из переменных окружения Vercel
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        return jsonify({'error': 'Критическая ошибка: Не настроен GROQ_API_KEY в Vercel!'}), 500

    try:
        if web_search:
            # 1. Просим ИИ вырезать ключевое слово для Википедии
            extract_prompt = (
                f"Извлеки из этого вопроса ОДНО или ДВА главных слова для поиска статьи в Википедии. "
                f"Ответь ТОЛЬКО этим ключевым словом в именительном падеже, без знаков препинания, кавычек и пояснений.\n"
                f"Вопрос: {question}"
            )
            
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": extract_prompt}]
            }
            
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            res_data = res.json()
            
            if "choices" in res_data:
                topic = res_data["choices"][0]["message"]["content"].strip().replace('"', '').replace('.', '')
            else:
                topic = question

            # 2. Поиск в Википедии
            page = wiki.page(topic)

            if page.exists():
                wiki_text = page.summary[0:2000]
                prompt = f"Информация из Википедии:\n{wiki_text}\n\nВопрос пользователя: {question}\nОтветь на русском языке, опираясь на факты выше."
            else:
                prompt = f"Пользователь спросил: {question}. Ответь на русском языке, так как статья '{topic}' не найдена в Википедии."
        else:
            prompt = question

        # 3. Финальный запрос к облачной Llama 3
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        final_res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        final_data = final_res.json()
        
        if "choices" in final_data:
            answer = final_data["choices"][0]["message"]["content"]
            return jsonify({'answer': answer})
        else:
            return jsonify({'error': 'Ошибка при ответе модели от Groq Cloud.'}), 500

    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)