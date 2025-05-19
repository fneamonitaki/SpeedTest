#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/time.h>

#define PORT 5555
#define BUFFER_SIZE (131072) //o server lambanei ara to read
#define TEST_DURATION 34
#define INTERVAL 2
#define SA struct sockaddr

double bytes_to_mbps(size_t bytes, double seconds) {
    return (bytes * 8.0) / (seconds * 1000000.0);
}

void handle_client(int client_fd) {
    char buffer[BUFFER_SIZE];
    struct timeval start_time, current_time, interval_start;
    gettimeofday(&start_time, NULL);
    gettimeofday(&interval_start, NULL);

    size_t total_received = 0;
    size_t received_this_interval = 0;

    while (1) {
        ssize_t received = recv(client_fd, buffer, BUFFER_SIZE, 0);
        if (received <= 0)
            break;

        total_received += received;
        received_this_interval += received;

        gettimeofday(&current_time, NULL);
        double elapsed_total = (current_time.tv_sec - start_time.tv_sec) +
                               (current_time.tv_usec - start_time.tv_usec) / 1000000.0;

        double elapsed_interval = (current_time.tv_sec - interval_start.tv_sec) +
                                  (current_time.tv_usec - interval_start.tv_usec) / 1000000.0;

        if (elapsed_interval >= INTERVAL) {
            double mbps = bytes_to_mbps(received_this_interval, elapsed_interval);
            static int interval_number = 0;
            printf("[SERVER] %2d–%2ds: Received %.2f Mbps\n",
                interval_number * INTERVAL,
                (interval_number + 1) * INTERVAL,
                mbps);
            interval_number++;
            received_this_interval = 0;
            gettimeofday(&interval_start, NULL);
}

        if (elapsed_total > TEST_DURATION)
            break;
    }

    double avg_mbps = bytes_to_mbps(total_received, TEST_DURATION);
    printf("[SERVER] Finished. Total received: %zu bytes (%.2f Mbps avg)\n", total_received, avg_mbps);
    close(client_fd);
}

int main() {
    int server_fd, client_fd;
    struct sockaddr_in servaddr, cliaddr;
    socklen_t len = sizeof(cliaddr);

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("Socket creation failed");
        printf("Socket creation failed\n\n");
        exit(EXIT_FAILURE);
    }
    

    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET; //IPv4
    servaddr.sin_addr.s_addr = htonl(INADDR_ANY);  // Accept from any IP
    servaddr.sin_port = htons(PORT);

    if (bind(server_fd, (SA*)&servaddr, sizeof(servaddr)) < 0) {
        perror("Bind failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, 5) != 0) {
        perror("Listen failed");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d...\n", PORT);

    while (1) {
        client_fd = accept(server_fd, (SA*)&cliaddr, &len);
        if (client_fd < 0) {
            perror("Accept failed");
            continue;
        }

        printf("Client connected from %s\n", inet_ntoa(cliaddr.sin_addr));
        handle_client(client_fd);
        printf("Ready for next client...\n\n");
    }

    close(server_fd);
    return 0;
}
