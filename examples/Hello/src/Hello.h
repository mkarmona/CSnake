#ifndef HELLO_H
#define HELLO_H

// Note that in windows, we need to specify which code in the dll must be exported (made visible to clients).
// CSnake has created a macro called HELLO_EXPORT for this purpose (in the file HelloWin32Header.h).
#include <HelloWin32Header.h>

void HELLO_EXPORT Hello();

#endif

