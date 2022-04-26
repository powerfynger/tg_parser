from cgitb import text
import requests
import telebot
from bs4 import BeautifulSoup
from config_bot import token
from config_bot import my_id
import schedule
from threading import Thread
from time import sleep
from telebot import types
from oauth2client.service_account import ServiceAccountCredentials
import gspread

HEADERS = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36', 'accept': '*/*'}

commands ={
    'статус' : 'Показывает статус аниме из списка.',
    'помощь' : 'Показывает список доступных команд.',
    'редактировать' : 'Команда для редактирования списка ссылок.',
    'подписка' : 'Подписывает на рассылку об отслеживаемых аниме.'
}
urls = []

#telebot
bot = telebot.TeleBot(token)

#Google api
scope = ['https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)



#Часть работы с google api
##############################################################################
def get_last_row(worksheet):
    str_list = list(filter(None, worksheet.col_values(1)))
    return len(str_list)

#Парсерная часть
########################################################################33

def get_html(url, params=None):
    try:
        r = requests.get(url, headers=HEADERS, params=params)
        return r
    except Exception:
        return -1

def get_content(html):
    soup = BeautifulSoup(html.text, 'html.parser')
    product = []
    test = soup.find_all('div', class_='value')
    status = soup.find('span', class_='b-anime_status_tag').get('data-text')
    if status != 'онгоинг':
        product.append({
            'name' : soup.find('h1').get_text(),
            'status' : status,
            'num_of_series' : test[1].get_text(strip=True),
            'raiting' : soup.find('div', class_='text-score').get_text(strip=True)[:4]
        })
    else:
        product.append({
            'name' : soup.find('h1').get_text(),
            'status' : status,
            'num_of_series' : test[1].get_text(strip=True),
            'raiting' : soup.find('div', class_='text-score').get_text(strip=True)[:4],
            'next_series' : test[2].get_text(strip=True) 
        })
        

        
    return product

def parse_one(url, message):
    chat_id = message.chat.id
    product = []
    html = get_html(url)
    if html.status_code == 200:
        product.extend(get_content(html))    
    else:
        bot.send_message(chat_id,f'Не удалось получить доступ по ссылке:{url}.')
    return product             

def parse_multi(message):
    sa = gspread.authorize(credentials)
    table = sa.open("shiki_urls")
    sheet = table.sheet1
    chat_id = message.chat.id
    products = []
    urls = []
    urls = sheet.get_all_values()
    for url in urls:
        html = get_html("".join(url))
        if html != -1:
            if html.status_code < 300 and html.status_code >= 200:
                products.extend(get_content(html))   
            else:
                bot.send_message(chat_id,f'Не удалось получить доступ по ссылке:{url}.')
    return products   

def parse_alredy_out():
    sa = gspread.authorize(credentials)
    table = sa.open("shiki_urls")
    sheet = table.sheet1
    products = []
    urls = sheet.get_all_values()
    for url in urls:
        html = get_html("".join(url))
        if html != -1:
            if html.status_code < 300 and html.status_code >= 200:
                product = get_content(html)
                if product[0]['status'] == 'вышло':
                    products.extend(get_content(html))
    # file.close()
    return products            

def check_anime():
    products = parse_alredy_out()
    id = my_id
    print(f'"{id}"')
    for product in products:
        name = product['name']
        if(name == 'вышло'):
            bot.send_message(id,f'Аниме: {name} вышло!')

def schedule_checker():
    # bot.polling()
    while True:
        schedule.run_pending()
        sleep(1)
#########################################################################

#Часть обработки сообщений пользователя
#########################################################################

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True,)
    markup.add(types.KeyboardButton('/помощь'))
    photo = open('/home/powerfyng/166ebd791adfb8222035cbbfacea4298.jpg', 'rb')
    bot.send_photo(chat_id, photo)
    msg = bot.send_message(chat_id, """\
        Ку, это первая версия аниме бота!
Пропиши команду /помощь, чтобы узнать больше.
        """, reply_markup=markup)

@bot.message_handler(commands=['статус'])
def command_status(message):
    chat_id = message.chat.id
    bot.reply_to(message, 'Хорошо, вот что сейчас находится в списке:')
    products = parse_multi(message)
    for product in products:
        name = product['name']
        status = product['status']
        num_of_series = product['num_of_series']
        raiting = product['raiting']
        if len(product) == 4:
            bot.send_message(chat_id,f'Аниме: {name}\nСтатус: {status}\nКол-во серий: {num_of_series}\nРейтинг: {raiting}')
        else:
            next_series = product['next_series']
            bot.send_message(chat_id,f'Аниме: {name}\nСтатус: {status}\nКол-во серий: {num_of_series}\nРейтинг: {raiting}\nСледующая серия: {next_series}')


@bot.message_handler(commands=['подписка'])
def command_sub_que(message):
    chat_id = message.chat.id
    choice = bot.reply_to(message, 'Подписаться на уведомления?\n1 - Да\n2 - Нет?')
    bot.register_next_step_handler(choice, sub1)

def sub1(message):
    chat_id = message.chat.id
    if message.text == '1':
        file = open('important_ids.txt', 'a')
        file.write(f'\n{str(message.chat.id)}')
        file.close()
        bot.send_message(chat_id, 'Вы успешно подписались на рассылку!')
    else:
        bot.send_message(chat_id, 'Вас поняла...')
        
@bot.message_handler(commands=['помощь'])
def command_help(message):
    chat_id = message.chat.id
    bot.reply_to(message, 'Список доступных команд:')
    for i in commands:
        bot.send_message(chat_id, f'/{i} - {commands[i]}')
    return 
    # markup = types.ReplyKeyboardMarkup()
    # itembut1 = types.KeyboardButton('/статус')
    # itembut2 = types.KeyboardButton('/редактировать')
    # itembut3 = types.KeyboardButton('/подписка')
    # markup.row(itembut1, itembut2)
    # markup.row(itembut3)
    # bot.send_message(chat_id, "Choose one letter:", reply_markup=markup)
    
@bot.message_handler(commands=['редактировать'])
def command_change_file_p1(message):
    chat_id = message.chat.id
    choice = bot.reply_to(message, '1 - Добавить ссылку в список\n2 - Удалить ссылку из списка.')
    bot.register_next_step_handler(choice, chf1)

def chf1(message):
    chat_id = message.chat.id
    choice = message.text
    if choice == '1':
        add_url = bot.send_message(chat_id, 'Отправьте ссылку на аниме из шики.')
        bot.register_next_step_handler(add_url, chf1_add)
    elif choice == '2':
        sa = gspread.authorize(credentials)
        table = sa.open("shiki_urls")
        sheet = table.sheet1
        i = 0
        urls = sheet.get_all_values()
        for url in urls:
            i += 1
            bot.send_message(chat_id, f'{i} - {"".join(url)}')
        delete_url = bot.send_message(chat_id, 'Отправьте номер аниме из списка, которое нужно удалить.')
        bot.register_next_step_handler(delete_url, chf1_del)
    else:
        bot.send_message(chat_id, f'Выбор {choice} является некорректным вариантом.')        

def chf1_add(message):
    
    chat_id = message.chat.id
    if get_html(message.text) == -1 or get_html(message.text).status_code != 200:
        bot.send_message(chat_id, 'Неудачная ссылка.')
    else:
        sa = gspread.authorize(credentials)
        table = sa.open("shiki_urls")
        sheet = table.sheet1
        sheet.update_cell(str(get_last_row(sheet)+1), 1, message.text)
        bot.send_message(chat_id, 'Ссылка успешно добавлена!')
    choice = bot.send_message(chat_id, 'Добавить ещё ссылку?\nДа\\Нет?')
    bot.register_next_step_handler(choice, chf2_add) 

def chf2_add(message):
    chat_id = message.chat.id
    if message.text == 'Да':
        add_url = bot.send_message(chat_id, 'Пожалуйста, отправьте ссылку на аниме из шики.')
        bot.register_next_step_handler(add_url, chf1_add) 
    else:
        bot.send_message(chat_id, 'Вас поняла.')
        exit()

def chf1_del(message):
    sa = gspread.authorize(credentials)
    table = sa.open("shiki_urls")
    sheet = table.sheet1
    chat_id = message.chat.id
    # i = 1
    i_del = int(message.text)
    last_row = get_last_row(sheet)
    for i in range(1, last_row+1):
        if i == i_del:
            sheet.delete_rows(i)
            sheet.add_rows(1)
            break
    bot.send_message(chat_id, 'Аниме успешно удалено!')

@bot.message_handler(commands=['test'])
def test(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup()
    itembtna = types.KeyboardButton('Да')
    itembtnv = types.KeyboardButton('Нет')
    itembtnc = types.KeyboardButton('/статус')
    itembtnd = types.KeyboardButton('/редактировать')
    itembtne = types.KeyboardButton('e')
    markup.row(itembtna, itembtnv)
    markup.row(itembtnc, itembtnd, itembtne)
    bot.send_message(chat_id, "Choose one letter:", reply_markup=markup)
################################################################################

def main():
    schedule.every(1).days.do(check_anime)
    Thread(target=schedule_checker).start()
    Thread(target=bot.polling()).start()

if __name__ == '__main__':
    # bot.send_message(chat_id,'ON')
    main()

        
        



# def test2(message):
#     chat_id = message.chat.id
#     bot.send_message(chat_id, message.text)
