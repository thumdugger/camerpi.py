from picamera2 import Picamera2

picam2 = Picamera2()
config = picam2.create_still_configuration()
picam2.configure(config)
picam2.start()

count = 0
while True:
    picam2.capture_file("test.jpg")
    print(f"Captured image {count}")
    count += 1
