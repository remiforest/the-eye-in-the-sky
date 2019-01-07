import cv2,sys,io,time
from io import StringIO
import numpy
from random import randint
from PIL import Image
from mapr.ojai.storage.ConnectionFactory import ConnectionFactory
from confluent_kafka import Consumer, KafkaError, Producer

# Parse args
read_topic = str(sys.argv[1])
write_topic = str(sys.argv[2])

print('### Detecting faces')

# Face detection params
cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

# Build Ojai MapRDB access
COUNT_MAPRDB_PATH = '/mapr/demo.mapr.com/frenchpatrol/detection_meta'  # Path for the table that stores people count
connection_str = "192.168.56.102:5678?auth=basic;user=mapr;password=mapr;ssl=false"
connection = ConnectionFactory().get_connection(connection_str=connection_str)
count_db_con = connection.get_or_create_store(COUNT_MAPRDB_PATH)
current_milli_time = lambda: int(round(time.time() * 1000))

# Build consumer
consumer_group = randint(2000, 2999)
consumer = Consumer({'group.id': consumer_group, 'default.topic.config': {'auto.offset.reset': 'earliest'}})
consumer.subscribe([read_topic])
# Build producer
dst_data = sys.argv[2].split(":")
dst_stream = str(dst_data[0])
dst_topic = str(dst_data[1])
producer = Producer({'streams.producer.default.stream': dst_stream})

running = True
frameId = 0
while running:
	msg = consumer.poll(timeout=1)
	if msg is None: continue
	if not msg.error():
		print('Reading from : ' + read_topic + ' Source Image ' + str(frameId))
		src_image_data = msg.value()
		src_image_io = Image.open(io.BytesIO(src_image_data))
		image_array = numpy.array(src_image_io)
		image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		faces = faceCascade.detectMultiScale(
		    gray,
		    scaleFactor=1.1,
		    minNeighbors=5,
		    minSize=(30, 30)
		)
		print('   -> Found {0} faces!'.format(len(faces)))
		curr_doc_id = current_milli_time()
		count_db_con.insert_or_replace(doc={'_id':str(curr_doc_id), 'drone_id':'1', 'people_count':len(faces)})
		for (x, y, w, h) in faces:
		    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
		# HUD dashboard
		height, width, channels = image.shape
		opacity = 0.2
		margins = 5
		overlay = image.copy()
		#Top Left box
		tlbox_width = 100
		tlbox_height = 100
		tlbox_xpos = margins
		tlbox_ypos = margins
		cv2.rectangle(overlay, (tlbox_xpos, tlbox_ypos), (tlbox_width, tlbox_height), (0, 255, 0), cv2.FILLED)
		cv2.rectangle(image, (tlbox_xpos, tlbox_ypos), (tlbox_width, tlbox_height), (0, 255, 0))
		#Bottom Left box
		blbox_width = 200
		blbox_height = 100
		blbox_xpos = margins
		blbox_ypos = height-blbox_height-margins
		cv2.rectangle(overlay, (blbox_xpos, blbox_ypos), (blbox_xpos+blbox_width, blbox_ypos+blbox_height), (0, 255, 0), cv2.FILLED)
		cv2.rectangle(image, (blbox_xpos, blbox_ypos), (blbox_xpos+blbox_width, blbox_ypos+blbox_height), (0, 255, 0))
		#Bottom Right radar
		brcircle_radius = 60
		brcircle_xpos = width-brcircle_radius-margins
		brcircle_ypos = height-brcircle_radius-margins
		cv2.circle(overlay, (brcircle_xpos, brcircle_ypos), brcircle_radius, (0, 255, 0), cv2.FILLED)
		cv2.circle(image, (brcircle_xpos, brcircle_ypos), brcircle_radius, (0, 255, 0))
		cv2.circle(image, (brcircle_xpos, brcircle_ypos), brcircle_radius-10, (0, 255, 0))
		cv2.circle(image, (brcircle_xpos, brcircle_ypos), brcircle_radius-20, (0, 255, 0))
		cv2.circle(image, (brcircle_xpos, brcircle_ypos), brcircle_radius-30, (0, 255, 0))
		cv2.circle(image, (brcircle_xpos, brcircle_ypos), brcircle_radius-40, (0, 255, 0))
		#Add overlay
		cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
		print('   -> Writing to : ' + write_topic)
		ret, jpeg = cv2.imencode('.png', image)
		producer.produce(dst_topic, jpeg.tobytes())
		#producer.flush()
	elif msg.error().code() != KafkaError._PARTITION_EOF:
		print(msg.error())
		running = False
	frameId += 1
#consumer.close()