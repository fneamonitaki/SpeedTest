#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/time.h>

#define PORT 5555
#define BUFFER_SIZE (64 * 1024) //This is the read buffer size because the server is receiving data
#define TEST_DURATION 34
#define INTERVAL 2
#define SA struct sockaddr

/**
 * Function to convert bytes to mbps
 * (based on wikipedia)
 */
double bytes_to_mbps(size_t bytes, double seconds) {
    return (bytes * 8.0) / (seconds * 1000000.0);
}

/**
 * function to handle each client at once for 30sec
 * ->receives TCP data from the client for 30 seconds
 * ->prints throughput in 2-second intervals
 * and 
 * ->prints average throughput at the end
 */
void handle_client(int client_fd) {
    //alocate a buffer for data
    char buffer[BUFFER_SIZE];
    struct timeval start_time, current_time, interval_start;
    //starting two timers
    //start_time is for the 30 seconds
    //interval_start is for 2sec windows
    gettimeofday(&start_time, NULL);
    gettimeofday(&interval_start, NULL);

    //initializing counter for total and interval data
    size_t total_received = 0;
    size_t received_this_interval = 0;

    int interval_number = 0;

    while (1) {
        //read data from client
        ssize_t received = recv(client_fd, buffer, BUFFER_SIZE, 0);
        //if this is true then something went wrong with the client
        //so exit the while loop
        if (received <= 0) 
            break;

        //update counters
        total_received += received;
        received_this_interval += received;



        //start a current timer 
        gettimeofday(&current_time, NULL);
        

        //The following code is for calculate timing
        //->measuring elapsed time with microsecond precision
        double elapsed_total = (current_time.tv_sec - start_time.tv_sec) +
                               (current_time.tv_usec - start_time.tv_usec) / 1000000.0;

        //double elapsed_interval = (current_time.tv_sec - interval_start.tv_sec) +
                               //   (current_time.tv_usec - interval_start.tv_usec) / 1000000.0;
        

        double elapsed_interval = (current_time.tv_sec - interval_start.tv_sec) +
                          (current_time.tv_usec - interval_start.tv_usec) / 1000000.0;

        if (elapsed_interval >= INTERVAL) {
            double mbps = bytes_to_mbps(received_this_interval, elapsed_interval);
            printf("[SERVER] %2d–%2ds: Received %.2f Mbps\n",
                interval_number * INTERVAL,
                (interval_number + 1) * INTERVAL,
                mbps);

            interval_number++;
            received_this_interval = 0;
            gettimeofday(&interval_start, NULL);
        }
                //this is ending the loop after 30 secs
                if (elapsed_total > TEST_DURATION)
                    break;
            }

    //at the end we calculate the total average throughput and print it
    double avg_mbps = bytes_to_mbps(total_received, TEST_DURATION);
    printf("[SERVER] Finished. Total received: %zu bytes (%.2f Mbps avg)\n", total_received, avg_mbps);
    //clode socket of client
    close(client_fd);
}

int main() {
    int server_fd, client_fd;
    struct sockaddr_in servaddr, cliaddr;
    socklen_t len = sizeof(cliaddr);

    /***
     * PF_INET = Internet version 4 protocols == AF_INET 
     * SOCK_STREAM = the socket has the indicated type, which specifies the semantics of communication
     * SOCK_STREAM = we use it for TCP! 
     * don't need to set protocol unless raw sockets! (thats why the 3rd attribute is 0)
     */

     //create socket
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        printf("Socket creation failed\n\n");
        exit(EXIT_FAILURE);
    }
    
    //bind socket, we need to bind an address to a local port
    memset(&servaddr, 0, sizeof(servaddr));
    servaddr.sin_family = AF_INET; //IPv4
    servaddr.sin_addr.s_addr = htonl(INADDR_ANY); //this is for accepting from all IP's
    servaddr.sin_port = htons(PORT);

    if (bind(server_fd, (SA*)&servaddr, sizeof(servaddr)) < 0) {
        printf("Bind failed\n");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    /**
     * we need to specify our socket and 5 is to specify a backlog,
     * which is how many outstanding connections the kernel can be waiting to pass off to
     * our aplication, if our application is slow to deal with inbound connections
     */

    //listen
    if (listen(server_fd, 5) != 0) {
        printf("Listen failed!");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d...\n", PORT);
    
    // Accept client connection
    //the server is running all time
    while (1) {
        //when we execute accept the system call will block until we get a new connection
        client_fd = accept(server_fd, (SA*)&cliaddr, &len);
        if (client_fd < 0) {
            printf("Accept failed");
            continue;
        }

        printf("Client connected from %s\n", inet_ntoa(cliaddr.sin_addr));
        //then the handle client is called and handles the 2 sec interval 
        handle_client(client_fd);
        printf("Ready for next client...\n\n");
    }

    close(server_fd);
    return 0;
}
