#trzeba dodać zwrotkę czasową 

import machine
from machine import deepsleep, Pin, SoftI2C, ADC
from time import sleep
from umqtt.simple import MQTTClient
import network
from libBME280 import BME280
###################################################
############# Konfiguracja urzadzenia #############
###################################################
"""
"""
#konfiguracja urz膮dzenia w sieci```````````````````````````````````
deviceID = "ESP32_2"
ssid = "DIR-853-C281"
password = "36400652" 
targetIPaddres = "192.168.0.168"
#dekraracja adres贸w pin贸w(zmienia膰 tylko w momencie zmiany projektu p艂ytki)
digital1Pin = 34
digital2Pin = 35
digital3Pin = 32
analog1Pin = 36 #piny nie dzia艂aj膮 dla gpio 4, 0, 12, 14
analog2Pin = 0
analog3Pin = 12
analog4Pin = 14
I2C1sclPin = 22
I2C1sdaPin = 21
#czy urz膮dzenie jest pod艂膮czone(numeracja urz膮dze艅 zgodna z schematem po艂膮cze艅 elektrycznych)
digital1Connection = True
digital2Connection = False
digital3Connection = False
analog1Connection = True
analog2Connection = False
analog3Connection = False
analog4Connection = False
I2C1Connection = True
#konfiguracja i2c
I2C1Freq = 500000
configuredAddresses = (24, 118) #krotka adres贸w urz膮dze艅 w przypadku dodania urz膮dzenia spoza listy nale偶y wpisa膰 tutaj kolejne urz膮dzenie oraz zdefiniowa膰 ifa w p臋tli g艂贸wnej
#ustawienie czas贸w 
timeMeasureBetween = 1 #czas u艣pienia urz膮dzenia pomi臋dzy kolejnymi odczytami w serii
timeMeasurement = 1 #czas u艣pienia urz膮dzenia pomi臋dzy kolejnymi seriami pomiarowymi
timeHard = 5000 #czas mocnego u艣pienia 
timeSoft = 2000 #czas lekkiego u艣pienia
services = []
###################################################
###################### klasy ######################
###################################################
"""
"""
class BME280unified:  #klasa zmieniaj膮ca nazw臋 metody read_compensated_data na value
  def __init__(self, I2C = None):
    self.BME = BME280(i2c = I2C)
  def getValue(self):
    return self.BME.read_compensated_data()
class MCP9808:
  def __init__(self, I2C):
    self.value = 0
    self.temp = 0
    self.address = 24
    self.I2C = I2C
    self.temp_reg = 5
    self.temp_reg_bytes = 2
  def getData(self):
    self.data = self.I2C.readfrom_mem(self.address, self.temp_reg, self.temp_reg_bytes)
    return self.data
  def getRawValue(self):
    self.data = self.getData()
    self.value = self.data[0] << 8 | self.data[1]
    return self.value
  def getValue(self):
    self.value = self.getRawValue()
    self.temp = (self.value & 0xFFF) / 16.0
    if self.value & 0x1000:
      self.temp -= 256.0
    return self.temp
class LDR:
  """
    klasa obs艂uguj膮ca czujnik LDR (o艣wietlenia)
  """
  adcRes = 0
  def __init__(self, pinID, min_value=0, max_value=100, adcRes = 4095):
    
    self.pinID = pinID
    self.min_value = min_value
    self.max_value = max_value
    self.adcRes = adcRes
    if self.min_value >= self.max_value:
      raise Exception('Min value is greater or equal to max value')
      
    self.adc = ADC(Pin(pinID))
    self.adc.atten(ADC.ATTN_11DB)
    
  def readADC(self):
    return self.adc.read()
    
  def logicValue(self, setLogicLevel):
    #odczyt warto艣ci logicznej zale偶nej od ustawionego fizycznie progu
    if self.readADC()/self.adcRes <= setLogicLevel:
      return True
    else:
      return False
  def adcVoltageValue(self):
    #Odczyt warto艣ci napi臋cia przeskalowane
    return self.readADC()/self.adcRes
  def getValue(self):
     # Konwersja na warto鑹ｈ啺 w luxach
    wartosc = ((self.max_value - self.min_value) * self.readADC()/self.adcRes)
    if  wartosc < 1/0.795:
      maxi =2000
    if wartosc >= 1/0.0399:
      maxi = 0
    if (wartosc < 1/0.0399 and wartosc > 1/0.795):
      maxi = (2649.3/wartosc)- 105.54
    return maxi
class reedSwitch:
  """
    klasa obs艂uguj膮ca kontraktron
    warunki fizyczne uruchomienia: 
      1.pod艂膮czenie kontraktronu do z艂膮cza
      2.kontrakton w stanie zamni臋tym w momencie inicjalizacji urz膮dzenia
  """
  def __init__(self, pinID):
    self.pinID = pinID
    self.resetTypeOfConnection()
    
  def getValue(self):
    #zwr贸cenie warto艣ci prz臋艂膮cznika
    value = self.button.value()
    if self.type == "PULL_DOWN":
      return not bool(value)
    else:
      return bool(value)
  def typeOfConnection(self):
    #zwr贸cenie typu przy艂膮czenia
    return self.type
  def resetTypeOfConnection(self):
    self.button = Pin(self.pinID, Pin.IN)
    print(self.button.value())
    #sprawdzenie czy zworka jest na pull up czy pull down. 
    test = self.button.value()
    if test == False:
      self.type = "DOWN"
      self.button = Pin(self.pinID, Pin.IN, Pin.PULL_UP)
      print(self.button.value())
    else:
      self.type = "UP"
      print(self.button.value())
      self.button = Pin(self.pinID, Pin.IN, Pin.PULL_DOWN)
###################################################
#################### funkcje ######################
###################################################
def do_connect():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
      sta_if.active(True)
      sta_if.connect(ssid, password)
      while not sta_if.isconnected():
        pass # wait till connection
    print('network config:', sta_if.ifconfig())
def listToString(str):
  strR = ""
  for ele in str:
    strR += ele
  return strR
def on_message(topic, msg):
    czas = msg
    h,m,s = [int(x) for x in czas.decode("utf-8").split(',')]
    print("Godzina: {}".format(h))
    print("Minuty: {}".format(m))
    print("Sekundy: {}".format(s))
    mod = m % 10
    time_mod = 9 - mod
    sek = 58-s
    time_ds = (time_mod*60) + sek
    print("Czekam {} minut".format((time_ds/60)))
    deepsleep(time_ds*1000)
###################################################
################# program g艂贸wny ##################
###################################################
"""
"""
def main():

  try:
    do_connect()
    CLIENT_NAME = deviceID
    BROKER_ADDR = targetIPaddres
    client = MQTTClient(CLIENT_NAME, BROKER_ADDR, keepalive=60)
    client.connect()
    if (machine.reset_cause() != machine.DEEPSLEEP_RESET):
      client.set_callback(on_message)
      client.subscribe("RP1/sys/time")
      client.publish("{}/sys/timeGet".format(deviceID), "Odczyt")
      print("Odczytywanie aktualnego czasu")
      client.wait_msg()
    if digital1Connection == True:
      reedSwitch1 = reedSwitch(digital1Pin)
      header = ("{}/services/kontraktron{}".format(deviceID,1), 0)
      services.append([header, reedSwitch1])
      print("configurate correct of {}: kontraktron {}".format(type(reedSwitch1), 1))    
    if digital2Connection == True:
      reedSwitch2 = reedSwitch(digital2Pin)
      header = ("{}/services/kontraktron{}".format(deviceID,2), 0)
      services.append([header, reedSwitch2])
      print("configurate correct of {}: kontraktron {}".format(type(reedSwitch2), 2))   
    if digital3Connection == True:
      reedSwitch3 = reedSwitch(digital3Pin)
      header = ("{}/services/kontraktron{}".format(deviceID,3), 0)
      services.append([header, reedSwitch3])
      print("configurate correct of {}: kontraktron {}".format(type(reedSwitch3), 3))
    if analog1Connection == True:
      LDR1 = LDR(analog1Pin)
      header = ("{}/services/czujnikSwiatla{}".format(deviceID,1), 0)
      services.append([header, LDR1])
      print("configurate correct of {}: czujnik swiatl;a {}".format(type(LDR1), 1))
    if analog2Connection == True:
      LDR2 = LDR(analog2Pin)
      header = ("{}/services/czujnikSwiatla{}".format(deviceID,2), 0)
      services.append([header, LDR2])
      print("configurate correct of {}: czujnik swiatla {}".format(type(LDR2), 2))
    if analog3Connection == True:
      LDR3 = LDR(analog3Pin)
      header = ("{}/services/czujnikSwiatla{}".format(deviceID,3), 0)
      services.append([header, LDR3])
      print("configurate correct of {}: czujnik swiatla {}".format(type(LDR3), 3))
    if analog4Connection == True:
      LDR4 = LDR(analog4Pin)
      header = ("{}/services/czujnikSwiatla{}".format(deviceID,4), 0)
      services.append([header, LDR4])
      print("configurate correct of {}: czujnik swiatla {}".format(type(LDR4), 4))
    if I2C1Connection == True:
      I2C1 = SoftI2C(scl=Pin(I2C1sclPin), sda=Pin(I2C1sdaPin), freq=I2C1Freq)
      print("configurate correct of {}: I2C {}".format(type(I2C1), 1))
      addressList = I2C1.scan()
      sumOfI2Cdivices = 0
      print("address list: {}".format(addressList))
      #tutaj dodaj ifa gdy nie ma urz膮dzenia na li艣cie
      if configuredAddresses[0] in addressList:
        MCP1 = MCP9808(I2C1)
        sumOfI2Cdivices += 1
        header = ("{}/services/MCP9808_{}/temperature".format(deviceID,1), 0)
        services.append([header, MCP1])
        print("configurate correct of {}: MCP9808 {}".format(type(MCP1), 1))
      if configuredAddresses[1] in addressList:
        BME1 = BME280unified(I2C = I2C1)
        sumOfI2Cdivices += 1
        header = ("{}/services/BME280_{}/temperature".format(deviceID,1), 0)
        services.append([header, BME1])
        header = ("{}/services/BME280_{}/humidity".format(deviceID,1), 0)
        services.append([header, BME1])
        header = ("{}/services/BME280_{}/presure".format(deviceID,1), 0)
        services.append([header, BME1])
        print("configurate correct of {}: BME280 {}".format(type(BME1), 1))
      if not addressList:
        print("pleas chack conection of I2C devices")
      print(len(configuredAddresses))
      if sumOfI2Cdivices < len(configuredAddresses):
        print("device/s nead be connected")#doda膰 w przysz艂o艣ci wy艣wietlanie urz膮ze艅 z tej listy
      if sumOfI2Cdivices > len(configuredAddresses):
        print("device/s nead be configurated")#doda膰 w przysz艂o艣ci wy艣wietlanie urz膮ze艅 z tej listy
      #dodaj klas臋 konfiguruj膮c膮 urz膮dzenie i2c
    #wys艂anie danych
#pętla głowna programu 
    while True:
      print("next measurement")
      print("start")
      serviceID = 1
      for service in services:
        #print(service)
        header = service[0][0]
        #print(header)
        
        if "BME280" in header:
          if "temperature" in header:
            data = "{}; {}".format(service[1].getValue()[0], serviceID)
            serviceID +=1
          if "humidity" in header:
            data = "{}; {}".format(service[1].getValue()[1], serviceID)
            serviceID +=1
          if "presure" in header:
            data = "{}; {}".format(service[1].getValue()[2], serviceID)
            serviceID +=1 
        else:
          data = "{}; {}".format(service[1].getValue(), serviceID) 
        client.publish(str(header), str(data).encode())
        serviceID +=1
        print(str(header).encode()+ "; " + str(data).encode())
      sleep(2)
      client.set_callback(on_message)
      client.subscribe("RP1/sys/time")
      client.publish("{}/sys/timeGet".format(deviceID), "Odczyt")
      print("Odczytywanie aktualnego czasu")
      client.wait_msg()
      print("end")
  #w momencie jekiegokolwiek błędu w programie
  except OSError as er:
    print(er)
    sleep(10)
    machine.reset()
main()


