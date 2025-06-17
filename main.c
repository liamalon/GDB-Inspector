#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <winsock2.h>

#pragma comment(lib, "ws2_32.lib")

#define BUF_SIZE 1024
#define PORT 8080

DWORD WINAPI ShellThread(LPVOID lpParam) {
    char input[BUF_SIZE];

    while (1) {
        printf("mini-shell> ");
        fflush(stdout);

        if (!fgets(input, BUF_SIZE, stdin)) {
            perror("fgets");
            continue;
        }

        input[strcspn(input, "\n")] = 0;  // remove newline

        if (_stricmp(input, "help") == 0) {
            printf("Available commands:\n");
            printf("  help            Show this help message\n");
            printf("  dir             List files in current directory\n");
            printf("  cat <filename>  Display contents of a file\n");
            printf("  exit            Exit the shell\n");
        } else if (_stricmp(input, "dir") == 0) {
            WIN32_FIND_DATA findFileData;
            HANDLE hFind = FindFirstFile("*", &findFileData);
            if (hFind == INVALID_HANDLE_VALUE) {
                printf("No files found.\n");
            } else {
                do {
                    printf("%s\n", findFileData.cFileName);
                } while (FindNextFile(hFind, &findFileData));
                FindClose(hFind);
            }
        } else if (_strnicmp(input, "cat ", 4) == 0) {
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
        } else if (_stricmp(input, "exit") == 0) {
            printf("Exiting shell.\n");
            exit(0);
        } else {
            printf("Unknown command: %s\n", input);
        }
    }

    return 0;
}

DWORD WINAPI TCPServerThread(LPVOID lpParam) {
    WSADATA wsa;
    SOCKET server, client;
    struct sockaddr_in server_addr, client_addr;
    int addrlen = sizeof(client_addr);
    char buffer[BUF_SIZE];
    const char* response = "all good\n";

    WSAStartup(MAKEWORD(2, 2), &wsa);
    server = socket(AF_INET, SOCK_STREAM, 0);
    if (server == INVALID_SOCKET) {
        printf("Socket creation failed\n");
        return 1;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server, (struct sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        printf("Bind failed\n");
        closesocket(server);
        return 1;
    }

    listen(server, 3);
    printf("TCP Server listening on port %d...\n", PORT);

    while (1) {
        client = accept(server, (struct sockaddr*)&client_addr, &addrlen);
        if (client == INVALID_SOCKET) {
            continue;
        }

        printf("Client connected.\n");

        while (1) {
            memset(buffer, 0, BUF_SIZE);
            int bytes = recv(client, buffer, BUF_SIZE - 1, 0);
            if (bytes <= 0) {
                break;
            }

            buffer[strcspn(buffer, "\r\n")] = 0;  // clean newline

            if (_stricmp(buffer, "exit") == 0) {
                printf("Client sent 'exit'. Closing connection.\n");
                break;
            }

            send(client, response, (int)strlen(response), 0);
        }

        closesocket(client);
        printf("Client disconnected.\n");
    }

    closesocket(server);
    WSACleanup();
    return 0;
}

int main() {
    HANDLE hShell, hServer;

    DWORD pid = GetCurrentProcessId();
    printf("Mini Shell Server started with PID: %lu\n", pid);
    
    hShell = CreateThread(NULL, 0, ShellThread, NULL, 0, NULL);
    hServer = CreateThread(NULL, 0, TCPServerThread, NULL, 0, NULL);

    WaitForSingleObject(hShell, INFINITE);
    WaitForSingleObject(hServer, INFINITE);

    return 0;
}
