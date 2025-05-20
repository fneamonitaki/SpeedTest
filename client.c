#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <time.h>
#include <sys/time.h>


#define SERVER_IP "127.0.01.1" //local IP for demo
//#define SERVER_IP "192.168.1.5" //IP for testings
#define SERVER_PORT 5555
#define BUFFER_SIZE (64 * 1024) //This is the write buffer size because the client is sending data
#define TEST_DURATION 32  
#define INTERVAL 2        
#define SA struct sockaddr


/**
 * Function to convert bytes to mbps
 * (based on wikipedia)
 * 1 Mbps = 1,000,000 bps
 */
double bytes_to_mbps(size_t bytes, double seconds) {
    return (bytes * 8.0) / (seconds * 1000000.0);  
}

int main() {
    int sock;
    struct sockaddr_in serv_addr;
    //alocate a buffer for data
    char buffer[BUFFER_SIZE];
    //this fills the buffer with dummy data
    memset(buffer, 'A', BUFFER_SIZE);  

    //create socket with the same way as server
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        printf("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    //assign IP, PORT
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(SERVER_PORT);
    serv_addr.sin_addr.s_addr = inet_addr(SERVER_IP); 

    //connect the client socket to server socket
    if (connect(sock, (SA*)&serv_addr, sizeof(serv_addr)) != 0) {
        printf("Connection failed");
        close(sock);
        exit(EXIT_FAILURE);
    }
    printf("Connected to server.\n");

    //start 2 timers, one for the 20 sec duartion and one for 2 sec interval
    struct timeval start_time, current_time, interval_start;
    gettimeofday(&start_time, NULL);
    gettimeofday(&interval_start, NULL);

    //initialize counters
    size_t total_sent = 0;
    size_t sent_this_interval = 0;

    while (1) {
        //sending data
        ssize_t sent = send(sock, buffer, BUFFER_SIZE, 0);
        if (sent < 0) { //if something goes wrong
            printf("Send error");
            break;
        }

        //update counters
        total_sent += sent;
        sent_this_interval += sent;

        //start a current timer 
        gettimeofday(&current_time, NULL);

        //The following code is for calculate timing
        //->measuring elapsed time with microsecond precision
        double elapsed_total = (current_time.tv_sec - start_time.tv_sec) +
                               (current_time.tv_usec - start_time.tv_usec) / 1000000.0;

        double elapsed_interval = (current_time.tv_sec - interval_start.tv_sec) +
                                  (current_time.tv_usec - interval_start.tv_usec) / 1000000.0;

        //every 2 secs print throuput 
        if (elapsed_interval >= INTERVAL) {
            double mbps = bytes_to_mbps(sent_this_interval, elapsed_interval);
            static int interval_number = 0;
            printf("[CLIENT] %2d–%2ds: Sent %.2f Mbps\n",
                interval_number * INTERVAL,
                (interval_number + 1) * INTERVAL,
                mbps);
            interval_number++;
            //reset the interval timer and counter
            sent_this_interval = 0;
            gettimeofday(&interval_start, NULL);
}
        //this is ending the loop after 30 secs
        if (elapsed_total >= TEST_DURATION) {
            break;
        }
    }
    //at the end we calculate the total average throughput and print it
    double final_mbps = bytes_to_mbps(total_sent, TEST_DURATION);
    printf("[CLIENT] Finished. Total sent: %zu bytes (%.2f Mbps avg)\n", total_sent, final_mbps);

    //close the socket
    close(sock);
    return 0;
}
