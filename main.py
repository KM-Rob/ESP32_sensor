from machine import *
from time import sleep
from bme680_v2 import *
from umqtt.simple import MQTTClient as mqtt
import wifi_esp as wifi

###################################################
############# Konfiguracja urzadzenia #############
###################################################

#Nazwa Urzadzenia
ID_Klienta = "***"

#Ustalenie ID_Czujnikow
#W przypadku braku ktoregos z czujnikow wpisac jakakolwiek wartosc np. 0
ID_BME680 = 0       #BME680
ID_Temperatura = 0  #Temperatura
ID_Oswietlenie = 0  #Oswietlenie
ID_Kontaktron = 0    #Otwarcie okna/drzwi

#W przypadku braku czujnika zmienic wartosc check na False
check_bme = False
check_temperatura = False
check_oswietlenie = False
ldr_pin = 33 #Pin podłączenia czujnika oświetlenia
check_kontaktron = False
kon_pin=14 #Pin podłączenia kontaktronu

#Piny do komunikacji I2C (dla ESP32 SDA = 21, SCL = 22)
SDA = Pin(21)
SCL = Pin(22)

#Czas soft rebootu przy wystąpieniu bledu
t_reboot = 60

###################################################
############### Koniec konfiguracji ###############
###################################################

###################################################
########### Definiowanie funkcji i klas ###########
###################################################

#Rezystancyjny czujnik oswietlenia LDR
class LDR:
    def __init__(self, pin, min_value=0, max_value=100):
        if check_oswietlenie == False:
            raise Exception('Brak czujnika oswietlenia (LDR)')
        if min_value >= max_value:
            raise Exception('Min value is greater or equal to max value')
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)
        self.min_value = min_value
        self.max_value = max_value
    def read(self):
        return self.adc.read()
    def getValue(self):
        value = (self.max_value - self.min_value) * self.read() / 4095
        if value < 1/0.795:
            max = 2000
        if value >= 1/0.0399:
            max = 0
        if (value < 1/0.0399 and value > 1/0.795):
            max = (2649.3/value) - 105.54
        return max

#Precyzyjny czujnik temperatury MCP9808
class MCP9808:
    def __init__(self,scl,sda):
        if check_temperatura == False:
            raise Exception("Brak czujnika temperatury MCP9808")
        self.value = 0
        self.temp = 0
        self.address = 24
        self.I2C = SoftI2C(scl,sda)
        self.I2C.scan()
        self.temp_reg = 5
        self.res_reg = 8
        self.temp_reg_bytes = 2
    def getData(self):
        self.data = self.I2C.readfrom_mem(self.address, self.temp_reg, self.temp_reg_bytes)
        return self.data
    def getValue(self):
        self.data = self.getData()
        self.value = self.data[0] << 8 | self.data[1]
        self.temp = (self.value & 0xFFF) / 16.0
        if self.value & 0x1000:
            self.temp -= 256.0
        return self.temp

#Czujnik otwarcia okna Kontaktron
class Kontaktron:
    def __init__(self, pin):
        if check_kontaktron == False:
            raise Exception('Nie podlaczono kontaktronu')
        self.pin = pin
        self.okno = Pin(self.pin, Pin.IN, Pin.PULL_UP)
    def getValue(self):
        if self.okno.value() == 0:
            stan = 'zamkniete'
        if self.okno.value() == 1:
            stan = 'otwarte'
        return stan

#Deepsleep na podstawie odebranego czasu 
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

#Funkcja pomiaru i MQTT BME680
def BME680(client,topic,scl,sda,ID):
    if check_bme == False:
        raise Exception('Brak czujnika BME680')
    bme = BME680_I2C(SoftI2C(scl,sda))
    temp1 = bme.temperature
    hum = bme.humidity
    pres = bme.pressure
    gas = bme.gas
    print('Temperatura: ', temp1)
    print('Wilgotność: ', hum)
    print('Ciśnienie: ', pres)
    print('Gaz: ', gas)
    message = ('{},{},{},{},{}'.format(temp1,hum,pres,gas,ID))
    client.publish(topic, message)
    print("Wysłano: " + str(message) + " do tematu " + topic)

#Funkcja MQTT dla czujnika z pojedynczym parametrem
def Czujnik_MQTT(client,topic,dane,ID):
    message = ('{},{}'.format(dane,ID))
    client.publish(topic, message)
    print("Wysłano: " + str(message) + " do tematu " + topic)

###################################################
###################### MAIN #######################
###################################################

def main():
    wifi.connect()  #Polaczenie z wifi
     
    Broker = "*.*.*.*"                #IP Brokera MQTT (IP Raspberry Pi)
    client = mqtt(ID_Klienta, Broker) #Utworzenie klienta
     
    #Polaczenie z Brokerem
    try:
        client.connect()
        print("Polaczono z Brokerem")
    except OSError:
        print("Blad polaczenia z Brokerem...")
        sleep(t_reboot)
        soft_reset()
         
      #Sprawdzenie przyczyny resetu oraz zapytanie o aktualny czas
    if (reset_cause() != DEEPSLEEP_RESET):
        try:
            client.set_callback(on_message)
            client.subscribe("SendTime")
            client.publish("GetTime", "Odczyt")
            print("Odczytywanie aktualnego czasu")
            client.wait_msg()
        except OSError:
            print("Blad polaczenia z Brokerem...")
            sleep(t_reboot)
            soft_reset()   
    #Pomiary poszczególnych czujników
    try:
        mcp = MCP9808(SCL,SDA)
        print('Temperatura = {}'.format(mcp.getValue()))
    except Exception as e:
        print(e)
    try:
        ldr = LDR(ldr_pin)
        print('Wartość światła = {}'.format(ldr.getValue()))
    except Exception as e:
        print(e)
    try:
        kon = Kontaktron(kon_pin)
        print('Okno jest {}'.format(kon.getValue()))
    except Exception as e:
        print(e)

    #Publikowanie MQTT
    try:
        if (check_bme == True):
            BME680(client,"BME680",SCL,SDA,ID_BME680)
        if (check_temperatura == True):
            Czujnik_MQTT(client,"Temperatura",mcp.getValue(),ID_Temperatura)
        if (check_oswietlenie == True):
            Czujnik_MQTT(client,"Oswietlenie",ldr.getValue(),ID_Oswietlenie)
        if (check_kontaktron == True):
            Czujnik_MQTT(client,"Kontaktron",kon.getValue(),ID_Kontaktron)
    except OSError:
        print("Blad polaczenia z Brokerem...")
        sleep(t_reboot)
        machine.soft_reset()
     
    #Deepsleep
    try:
        client.set_callback(on_message)
        client.subscribe("SendTime")
        client.publish("GetTime", "Odczyt")
        print("Odczytywanie aktualnego czasu")
        client.wait_msg()
    except OSError:
        print("Blad polaczenia z Brokerem...")
        sleep(t_reboot)
        machine.soft_reset()        
main()
