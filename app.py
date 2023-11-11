from flask import Flask, render_template, request, jsonify
from kafka import KafkaProducer, KafkaConsumer
from threading import Thread
import queue

app = Flask(__name__)

#Productor y consumidor de Kafka
producer = KafkaProducer(bootstrap_servers=['10.20.10.10:9092'])
consumer = KafkaConsumer('chat', bootstrap_servers=['10.20.10.10:9092'], auto_offset_reset='earliest')

message_queue = queue.Queue()

def kafka_consumer_thread():
    for message in consumer:
        message_queue.put(message.value.decode())

consumer_thread = Thread(target=kafka_consumer_thread, daemon=True)
consumer_thread.start()

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/send', methods=['POST'])
def send_message():
    data = request.json
    message = data.get('message')
    if message:
        producer.send('chat', message.encode())
        return jsonify({'status': 'Mensaje enviado'}), 200
    else:
        return jsonify({'error': 'No se proporcionó mensaje'}), 400

@app.route('/receive')
def receive_message():
    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get())
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=True)