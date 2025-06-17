#include <stdio.h>
void foo() { printf("in foo\n"); }
void bar() { printf("in bar\n"); }

int main() {
    while (1) {
        foo();
        bar();
        sleep(1);
    }
    return 0;
}
