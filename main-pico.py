import time
from pixel_ring import pixel_ring
import json
import sys
import paho.mqtt.client as mqtt
import logging
from logging.handlers import RotatingFileHandler
import os
import distro
from picovoice import Picovoice
from pvrecorder import PvRecorder
import zahlwort2num

z2n = zahlwort2num

handler = RotatingFileHandler(
    '/home/pi/voice-assistant/pico.log',
    mode = 'a',
    maxBytes= 2000000,
    backupCount= 1,
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%d-%b-%y %H:%M:%S")
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)
logging.info("Started by a user or deamon")

broker = '192.168.30.9'
port = 1883

client = mqtt.Client("P1")

try:
   client.connect(broker, port)
   logging.info("Connection to Broker Succesfull!")
except Exception as err:
   logging.error('Failed to connect to mqtt Broker', err)

def on_disconnect():
   try:
      client.reconnect()
      logging.info("Reconnected successfully!")
      return
   except Exception as err:
      logging.error("%s. Reconnect failed. Retrying...", err)

client.on_disconnect = on_disconnect

ACCESS_KEY = 'UHqNPD8rCVOJsH8MYks3vchv5xqoWWiE7j7cSPgyJDjrIkTP5mq1uw=='

rolladenZustanddict = {
   "auf": 100,
   "zu": 0,
   "hoch": 100,
   "runter": 0,
}

# wake word detected
def wake_word_callback():
   logging.info("Wake on Word detcted!")
   pixel_ring.set_brightness(30)
   pixel_ring.speak()

def inference_callback(inference):
   if inference.is_understood:
      pixel_ring.think()
      intent = ''
      intent = inference.intent
      slots = inference.slots
      logging.info("Intent detected:")
      logging.info(intent)
      logging.info("and following slots:")
      logging.info(slots)
      if intent == 'lichter':
         out = json.loads(json.dumps(slots))
         logging.info("Zustand:")
         logging.info(out['zustand'])
         logging.info('Ort:')
         logging.info(out['ort'])
         if out['ort']:
            if out['ort'] == 'mitte':
               if out['zustand'] == 'an':
                  client.publish("main/hm/manuel/licht/panel", "1")
               elif out['zustand'] == 'aus':
                  client.publish("main/hm/manuel/licht/panel", "0")
               else:
                  logging.warning("failed to understand Zustand")
                  pixel_ring.off()
                  return 0
            if out['ort'] == 'süd':
               if out['zustand'] == 'an':
                  client.publish("main/hm/manuel/licht/süd", "1")
               elif out['zustand'] == 'aus':
                  client.publish("main/hm/manuel/licht/süd", "0")
               else:
                  logging.warning("failed to understand Zustand")
                  pixel_ring.off()
                  return 0
            if out['ort'] == 'nord':
               if out['zustand'] == 'an':
                  client.publish("main/hm/manuel/licht/nord", "1")
               elif out['zustand'] == 'aus':
                  client.publish("main/hm/manuel/licht/nord", "0")
               else:
                  logging.warning("failed to understand Zustand")
                  pixel_ring.off()
                  return 0
            if out['ort'] == 'bett':
               if out['zustand'] == 'an':
                  client.publish("main/hm/manuel/licht/bett", "1")
               elif out['zustand'] == 'aus':
                  client.publish("main/hm/manuel/licht/bett", "0")
               else:
                  logging.warning("failed to understand Zustand")
                  pixel_ring.off()
                  return 0
            else:
               logging.warning("failed to understand Ort")
               pixel_ring.off()
               return 0
         else:
            if out['zustand'] == 'an':
               client.publish("main/hm/manuel/licht/panel", "1")
            elif out['zustand'] == 'aus':
               client.publish("main/hm/manuel/licht/panel", "0")
            else:
               logging.warning("failed to understand Zustand")
               pixel_ring.off()
               return 0
      if intent == 'stopen':
         pixel_ring.off()
         logging.warning('System has been shutdown by the user')
         os.system("sudo shutdown +1")
         sys.exit(0)
      if intent == 'rolladen':
         out = json.loads(json.dumps(slots))
         logging.info("Zustand:")
         logging.info(out['zustand'])
         if out['zustand'] in rolladenZustanddict:
            logging.info(rolladenZustanddict[out['zustand']])
            client.publish("main/hm/manuel/rolladen", rolladenZustanddict[out['zustand']])
         elif z2n.convert(out['zustand']):
            client.publish("main/hm/manuel/rolladen", z2n.convert(out['zustand']))
         else:
            logging.info("failed to understand Zustand")
            pixel_ring.off()
            return 0
      pixel_ring.off()
      return 0
   else:
      i = 50
      while(i>0):
         pixel_ring.set_brightness(i)
         time.sleep(0.01)
         i -= 1
      pixel_ring.off()
if distro.id() == "raspbian":
   keywordfile = '/home/pi/voice-assistant/Hey-Computer_de_raspberry-pi_v2_2_0.ppn'
   contextfile = '/home/pi/voice-assistant/Licht_de_raspberry-pi_v2_2_0.rhn'
else:
   keywordfile = 'Hey-Computer_de_linux_v2_2_0.ppn'
picovoice = Picovoice(
     access_key=ACCESS_KEY,
     keyword_path=keywordfile,
     porcupine_model_path='/home/pi/voice-assistant/porcupine_params_de.pv',
     wake_word_callback=wake_word_callback,
     context_path=contextfile,
     rhino_model_path='/home/pi/voice-assistant/rhino_params_de.pv',
     inference_callback=inference_callback,
     endpoint_duration_sec=0.5,
     require_endpoint=False)

logging.info('Following Audio Devices were detected')
for i, device in enumerate(PvRecorder.get_available_devices()):
   logging.info('Device %d: %s' % (i, device))

recorder = PvRecorder(
        frame_length=picovoice.frame_length,
        device_index=1
        )
recorder.start()


if __name__ == '__main__':
   pixel_ring.off()
   client.loop_start()
   while True:
      picovoice.process(recorder.read())
