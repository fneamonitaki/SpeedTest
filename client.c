#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <time.h>
#include <sys/time.h>

#define SERVER_IP "127.0.0.1" // <-- CHANGE to your server's IP
#define SERVER_PORT 12345
#define BUFFER_SIZE 1024
#define TEST_DURATION 30  // seconds
#define INTERVAL 2        // seconds
#define SA struct sockaddr

// Convert bytes to Mbps
double bytes_to_mbps(size_t bytes, double seconds) {
    return (bytes * 8.0) / (seconds * 1000000.0);  // 1 Mbps = 1,000,000 bps
}

int main() {
    int sock;
    struct sockaddr_in serv_addr;
    char buffer[BUFFER_SIZE];
    memset(buffer, 'A', BUFFER_SIZE);  // Fill buffer with dummy data

    // Create socket
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    int size = 212992; // ή 524288 για μεγαλύτερο
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &size, sizeof(size));
    
    // Setup server address
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(SERVER_PORT);
    serv_addr.sin_addr.s_addr = inet_addr(SERVER_IP);  // Use real IP

    // Connect to server
    if (connect(sock, (SA*)&serv_addr, sizeof(serv_addr)) != 0) {
        perror("Connection failed");
        close(sock);
        exit(EXIT_FAILURE);
    }
    printf("Connected to server.\n");

    // Timing setup
    struct timeval start_time, current_time, interval_start;
    gettimeofday(&start_time, NULL);
    gettimeofday(&interval_start, NULL);

    size_t total_sent = 0;
    size_t sent_this_interval = 0;

    while (1) {
        // Send data
        ssize_t sent = send(sock, buffer, BUFFER_SIZE, 0);
        if (sent < 0) {
            perror("Send error");
            break;
        }
        total_sent += sent;
        sent_this_interval += sent;

        // Check time
        gettimeofday(&current_time, NULL);
        double elapsed_total = (current_time.tv_sec - start_time.tv_sec) +
                               (current_time.tv_usec - start_time.tv_usec) / 1000000.0;

        double elapsed_interval = (current_time.tv_sec - interval_start.tv_sec) +
                                  (current_time.tv_usec - interval_start.tv_usec) / 1000000.0;

        if (elapsed_interval >= INTERVAL) {
            double mbps = bytes_to_mbps(sent_this_interval, elapsed_interval);
            printf("[CLIENT] Sent %.2f Mbps in last %.1f sec\n", mbps, elapsed_interval);
            sent_this_interval = 0;
            gettimeofday(&interval_start, NULL);  // Reset interval timer
        }

        if (elapsed_total >= TEST_DURATION) {
            break;
        }
    }

    double final_mbps = bytes_to_mbps(total_sent, TEST_DURATION);
    printf("[CLIENT] Finished. Total sent: %zu bytes (%.2f Mbps avg)\n", total_sent, final_mbps);

    close(sock);
    return 0;
}
