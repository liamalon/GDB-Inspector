#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <dirent.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define BUF_SIZE 1024
#define PORT 8080

void* ShellThread(void* arg) {
    char input[BUF_SIZE];

    while (1) {
        printf("mini-shell> ");
        fflush(stdout);

        if (!fgets(input, BUF_SIZE, stdin)) {
            perror("fgets");
            continue;
        }

        input[strcspn(input, "\n")] = 0;  // remove newline

        if (strcasecmp(input, "help") == 0) {
            printf("Available commands:\n");
            printf("  help            Show this help message\n");
            printf("  dir             List files in current directory\n");
            printf("  cat <filename>  Display contents of a file\n");
            printf("  exit            Exit the shell\n");
        } else if (strcasecmp(input, "dir") == 0) {
            DIR* d = opendir(".");
            if (!d) {
                perror("opendir");
            } else {
                struct dirent* dir;
                while ((dir = readdir(d)) != NULL) {
                    printf("%s\n", dir->d_name);
                }
                closedir(d);
            }
        } else if (strncasecmp(input, "cat ", 4) == 0) {
            char* filename = input + 4;
            FILE* f = fopen(filename, "r");
            if (!f) {
                perror("fopen");
                continue;
            }
            char line[BUF_SIZE];
            while (fgets(line, BUF_SIZE, f)) {
                printf("%s", line);
            }
            fclose(f);
        } else if (strcasecmp(input, "exit") == 0) {
            printf("Exiting shell.\n");
            exit(0);
        } else {
            printf("Unknown command: %s\n", input);
        }
    }

    return NULL;
}

void* TCPServerThread(void* arg) {
    int server_fd, client_fd;
    struct sockaddr_in server_addr, client_addr;
    socklen_t addrlen = sizeof(client_addr);
    char buffer[BUF_SIZE];
    const char* response = "all good\n";

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return NULL;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        close(server_fd);
        return NULL;
    }

    listen(server_fd, 3);
    printf("TCP Server listening on port %d...\n", PORT);

    while (1) {
        client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &addrlen);
        if (client_fd < 0) {
            perror("accept");
            continue;
        }

        printf("Client connected.\n");

        while (1) {
            memset(buffer, 0, BUF_SIZE);
            int bytes = recv(client_fd, buffer, BUF_SIZE - 1, 0);
            if (bytes <= 0) {
                break;
            }

            buffer[strcspn(buffer, "\r\n")] = 0;

            if (strcasecmp(buffer, "exit") == 0) {
                printf("Client sent 'exit'. Closing connection.\n");
                break;
            }

            send(client_fd, response, strlen(response), 0);
        }

        close(client_fd);
        printf("Client disconnected.\n");
    }

    close(server_fd);
    return NULL;
}

int main() {
    pthread_t shell_thread, server_thread;

    printf("Mini Shell Server started with PID: %d\n", getpid());

    pthread_create(&shell_thread, NULL, ShellThread, NULL);
    pthread_create(&server_thread, NULL, TCPServerThread, NULL);

    pthread_join(shell_thread, NULL);
    pthread_join(server_thread, NULL);

    return 0;
}
