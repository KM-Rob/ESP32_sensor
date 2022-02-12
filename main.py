import machine
from machine import deepsleep, Pin, SoftI2C, ADC
from time import sleep
from BME_lib import BME
from umqtt.simple import MQTTClient as mqtt
import wifi_new as wifi

###################################################
############# Konfiguracja urzadzenia #############
###################################################

#Nazwa Urzadzenia
ID_Klienta = "ESP32_2"

#Ustalenie ID_Czujnikow
#W przypadku braku ktoregos z czujnikow wpisac cokolwiek 
ID_BME280 = 0       #BME280
ID_Temperatura = 3  #Temperatura
ID_Oswietlenie = 4  #Oswietlenie
ID_Glosnosc = 0     #Glosnosc

#W przypadku braku czujnika oswietleni lub glosnosci zmienic wartosc check na 0
check_oswietl = 1
check_glos = 0

#Rodzaj zasilania - Z sieci = 0, Z akumulatora = 1
check_aku = 0

#Ustalenie ID_Akumulatora (jesli check_aku = 1 jesli = 0 to wartosc nie ma znaczenia)
ID_Akumulator = 1

###################################################
############### Koniec konfiguracji ###############
###################################################

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

#funkcja MQTT dla BME280
def BME280(client,topic,temp,wilg,cisn,ID):
    
    message = ('{},{},{},{}'.format(temp,wilg,cisn,ID))
    client.publish(topic, message)
    print("Wysłano: " + str(message) + " do tematu " + topic)

#funkcja MQTT dla czujnika z pojedynczym parametrem
def Czujnik(client,topic,dane,ID):
    
    message = ('{},{}'.format(dane,ID))
    client.publish(topic, message)
    print("Wysłano: " + str(message) + " do tematu " + topic)

def main():

    wifi.connect()  #Polaczenie z wifi
    
    Broker = "x.x.x.x"           #Ip Brokera MQTT
    client = mqtt(ID_Klienta, Broker) #Utworzenie klienta
    
    #Polaczenie z Brokerem
    try:
        client.connect()      
    except OSError:
        print("Blad polaczenia z Brokerem...")
        sleep(5*60)
        machine.soft_reset()
        
    
    #Sprawdzenie przyczyny resetu oraz zapytanie o aktualny czas
    if (machine.reset_cause() != machine.DEEPSLEEP_RESET):
        try:
            client.set_callback(on_message)
            client.subscribe("SendTime")
            client.publish("GetTime", "Odczyt")
            print("Odczytywanie aktualnego czasu")
            client.wait_msg()
        except OSError:
            print("Blad polaczenia z Brokerem...")
            sleep(5*60)
            machine.soft_reset()
      
###################
       #Temperature
    try:
        #Ustawienia I2C
        i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
        i2c.scan()
        #Operacje pamięci
        address = 24
        temp_reg = 5
        #Odczyt wartości rejestru
        data = i2c.readfrom_mem(address, temp_reg, 2)
        #Funkcja zamiant na stopnie Celsjusza
        def temp_c(data):
            value = data[0] << 8 | data[1]
            temp = (value & 0xFFF) / 16.0
            if value & 0x1000:
                temp -= 256.0
            return temp
        temp_2 = temp_c(data)
        #
        check_temp = 1
        print('Temperatura = {}'.format(temp_c(data)))
    except:
        check_temp = 0
        print('Brak czujnika Temperatury')
        temp_2=0
      #BME280
    try:
        #Ustawienia I2C
        i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)
        #Użycie funkcji z biblioteki
        bme = BME(i2c=i2c)
        #odczytywanie poszczególnych elementów zmiennej
        temp1 = bme.temperature
        hum = bme.humidity
        pres = bme.pressure
        #
        check_bme = 1
        print('Temperatura: ', temp1)
        print('Wilgotność: ', hum)
        print('Ciśnienie: ', pres)
    except:
        check_bme = 0
        temp1=0
        hum=0
        pres=0
        print('Brak czujnika BME280')
    #Light
    #Klasa odczytu wartości rezystora
    class LDR:
        #Inicjacja podstawowego zakresu
        def __init__(self, pin, min_value=0, max_value=100):
            if min_value >= max_value:
                raise Exception('Min value is greater or equal to max value')
            #Inicjacja konwersji analogowo-cyfrowej
            self.adc = ADC(Pin(pin))
            #Ustawienie tłumiemnia wejścia
            self.adc.atten(ADC.ATTN_11DB)
            self.min_value = min_value
            self.max_value = max_value
        #Odczyt wartości związanych z klasy LDR
        def read(self):
            return self.adc.read()

        def value(self):
             # Konwersja na wartość w luxach
            wartosc = ((self.max_value - self.min_value) * self.read()/ 4095)
            if  wartosc < 1/0.795:
                maxi =2000
            if wartosc >= 1/0.0399:
                maxi = 0
            if (wartosc < 1/0.0399 and wartosc > 1/0.795):
                maxi = (2649.3/wartosc)- 105.54
            return maxi
    ldr = LDR(34)
    light = ldr.value()
    print('Wartość światła = {}'.format(light))
    #except:    
        #light = ('Brak czujnika światła')
        #print(light)
    ###################
    
    #Publikowanie MQTT
    try:
        #MQTT BME280
        if (check_bme == 1):
            BME280(client,"BME280",temp1,hum,pres,ID_BME280)
        
        #MQTT Temperatura
        if (check_temp == 1):
            Czujnik(client,"Temperatura",temp_2,ID_Temperatura)

        #MQTT Oswietlenie
        if (check_oswietl == 1):
            Czujnik(client,"Oswietlenie",light,ID_Oswietlenie)
        
        #MQTT Glosnosc
        if (check_glos == 1):
            Czujnik(client,"Glosnosc",glos,ID_Glosnosc)
        
        #MQTT Akumulator
        if (check_aku == 1):
            Czujnik(client,"Akumulator",stan,ID_Akumulator)
            
    except OSError:
        print("Blad polaczenia z Brokerem...")
        sleep(5*60)
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
        sleep(5*60)
        machine.soft_reset()
    
main()  

