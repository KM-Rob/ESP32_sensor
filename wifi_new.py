def connect():
    import network
    from time import sleep
    
    #Dane do logowania
    ssid = "****"
    password = "****"
    
    #utworzenie obiektu dla polaczenia wlan
    stat = network.WLAN(network.STA_IF)
    stat.active(True)
    
    #sprawdzenie czy polaczono
    if stat.isconnected() == True:
        print("Polaczono")
    else:
        stat.connect(ssid, password)
        while stat.isconnected() == False:
            print("Nieudane polaczenie z Wifi")
            print("Ponawiam...")
            sleep(2)
            
    #informacja o poprawnym polaczeniu
    print("Polaczenie z Wifi zakonczone sukcesem")
    print(stat.ifconfig())