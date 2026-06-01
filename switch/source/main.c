#include <string.h>
#include <stdio.h>
#include <switch.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MAGIC "NX2T"
#define PORT 28275

#pragma pack(push, 1)
struct NX2TPacket {
    char magic[4];
    u8 version;
    u8 type;          // 0 = touch, 1 = heartbeat, 2 = disconnect
    u8 touch_count;
    u8 reserved;
    u64 timestamp;
    struct {
        u32 finger_id;
        u16 x;
        u16 y;
        u16 diameter_x;
        u16 diameter_y;
    } touches[16];
};
#pragma pack(pop)

int main(int argc, char **argv) {
    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    
    hidInitializeTouchScreen();
    
    SocketInitConfig config = *socketGetDefaultInitConfig();
    config.udp_tx_buf_size = 0x4000;
    config.udp_rx_buf_size = 0x4000;
    Result rc = socketInitialize(&config);
    if (R_FAILED(rc)) {
        printf("socketInitialize failed: %08X\n", rc);
    }
    
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    
    u8 ip[4] = {192, 168, 1, 100};
    int selected_field = 0; // 0-3 for IP
    bool running = true;
    bool connected = false;
    
    struct sockaddr_in dest;
    memset(&dest, 0, sizeof(dest));
    dest.sin_family = AF_INET;
    dest.sin_port = htons(PORT);
    
    s32 last_count = -1;
    
    while(appletMainLoop() && running) {
        padUpdate(&pad);
        u64 kDown = padGetButtonsDown(&pad);
        
        if (kDown & HidNpadButton_Plus) break; // Exit
        
        consoleClear();
        printf("\x1b[1;1HNX2Touchpad Sender\n");
        printf("------------------\n\n");
        
        if (!connected) {
            printf("Setup Target IP Address:\n\n");
            
            for (int i = 0; i < 4; i++) {
                if (i == selected_field) printf("[ ");
                printf("%d", ip[i]);
                if (i == selected_field) printf(" ]");
                if (i < 3) printf(" . ");
            }
            
            printf("\n\nControls:\n");
            printf("  D-Pad Left/Right : Select octet\n");
            printf("  D-Pad Up/Down    : Change value\n");
            printf("  A                : Connect\n");
            printf("  +                : Exit\n");
            
            if (kDown & HidNpadButton_Left) selected_field = (selected_field - 1 + 4) % 4;
            if (kDown & HidNpadButton_Right) selected_field = (selected_field + 1) % 4;
            if (kDown & HidNpadButton_Up) ip[selected_field] = (ip[selected_field] + 1) % 256;
            if (kDown & HidNpadButton_Down) ip[selected_field] = (ip[selected_field] - 1 + 256) % 256;
            
            if (kDown & HidNpadButton_A) {
                char ip_str[16];
                sprintf(ip_str, "%d.%d.%d.%d", ip[0], ip[1], ip[2], ip[3]);
                inet_aton(ip_str, &dest.sin_addr);
                connected = true;
                last_count = -1; // reset state
            }
        } else {
            printf("Target IP: %d.%d.%d.%d\n\n", ip[0], ip[1], ip[2], ip[3]);
            printf("Status: TRANSMITTING...\n\n");
            printf("Touch the screen to send data.\n");
            printf("Press B to change IP.\n");
            printf("Press + to exit.\n");
            
            if (kDown & HidNpadButton_B) {
                connected = false;
                // Send disconnect packet
                struct NX2TPacket pkt;
                memset(&pkt, 0, sizeof(pkt));
                memcpy(pkt.magic, MAGIC, 4);
                pkt.version = 1;
                pkt.type = 2; // Disconnect
                sendto(sock, &pkt, sizeof(pkt), 0, (struct sockaddr*)&dest, sizeof(dest));
            } else {
                HidTouchScreenState state={0};
                if (hidGetTouchScreenStates(&state, 1)) {
                    // Only send if we have touches or if we just transitioned to 0 touches
                    if (state.count > 0 || (last_count > 0 && state.count == 0)) {
                        struct NX2TPacket pkt;
                        memset(&pkt, 0, sizeof(pkt));
                        memcpy(pkt.magic, MAGIC, 4);
                        pkt.version = 1;
                        pkt.type = 0;
                        pkt.timestamp = state.sampling_number;
                        pkt.touch_count = state.count;
                        
                        for (int i=0; i<state.count; i++) {
                            pkt.touches[i].finger_id = state.touches[i].finger_id;
                            pkt.touches[i].x = state.touches[i].x;
                            pkt.touches[i].y = state.touches[i].y;
                            pkt.touches[i].diameter_x = state.touches[i].diameter_x;
                            pkt.touches[i].diameter_y = state.touches[i].diameter_y;
                        }
                        
                        size_t packet_size = 16 + (state.count * 12);
                        sendto(sock, &pkt, packet_size, 0, (struct sockaddr*)&dest, sizeof(dest));
                    }
                    last_count = state.count;
                }
            }
        }
        
        consoleUpdate(NULL);
    }
    
    // Disconnect on exit
    if (connected) {
        struct NX2TPacket pkt;
        memset(&pkt, 0, sizeof(pkt));
        memcpy(pkt.magic, MAGIC, 4);
        pkt.version = 1;
        pkt.type = 2; // Disconnect
        sendto(sock, &pkt, sizeof(pkt), 0, (struct sockaddr*)&dest, sizeof(dest));
    }
    
    if (sock >= 0) close(sock);
    socketExit();
    consoleExit(NULL);
    return 0;
}
