/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "ui.h"
#include "core_bridge.h"
#include <EGL/egl.h>
#include <EGL/eglext.h>
#define GL_GLEXT_PROTOTYPES 1
#include <GL/glcorearb.h>
#include <ps5_opengl_display_modes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int sceUserServiceInitialize(const void *params);
extern int sceUserServiceGetInitialUser(int *user);
extern int sceUserServiceTerminate(void);
extern int scePadInit(void);
extern int scePadOpen(int user, int type, int index, const void *params);
extern int scePadReadState(int handle, void *buffer);
extern int scePadClose(int handle);
extern uint64_t sceKernelGetProcessTime(void);
extern int sceKernelUsleep(unsigned microseconds);

static void logs(void) {
  FILE *f = freopen("/download0/rpcs3-ps5-frontend.log", "a", stdout);
  if (f) setvbuf(f, NULL, _IONBF, 0);
  f = freopen("/download0/rpcs3-ps5-frontend.log", "a", stderr);
  if (f) setvbuf(f, NULL, _IONBF, 0);
}
static GLuint shader(GLenum type, const char *source) {
  GLuint s = glCreateShader(type);
  glShaderSource(s, 1, &source, NULL);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char message[2048];
    glGetShaderInfoLog(s, sizeof(message), NULL, message);
    fprintf(stderr, "Shader compilation: %s\n", message);
    glDeleteShader(s);
    return 0;
  }
  return s;
}
static GLuint program(void) {
  const char *vs = "#version 330 core\nlayout(location=0)in vec2 p;layout(location=1)in vec2 uv;out vec2 t;void main(){t=uv;gl_Position=vec4(p,0,1);}";
  const char *fs = "#version 330 core\nin vec2 t;out vec4 color;uniform sampler2D tex;void main(){color=texture(tex,t);}";
  GLuint v = shader(GL_VERTEX_SHADER, vs), f = shader(GL_FRAGMENT_SHADER, fs);
  if (!v || !f) { if (v) glDeleteShader(v); if (f) glDeleteShader(f); return 0; }
  GLuint p = glCreateProgram();
  glAttachShader(p, v); glAttachShader(p, f); glLinkProgram(p); glDeleteShader(v); glDeleteShader(f);
  GLint ok = 0; glGetProgramiv(p, GL_LINK_STATUS, &ok);
  if (!ok) { char message[2048]; glGetProgramInfoLog(p, sizeof(message), NULL, message); fprintf(stderr, "Program link: %s\n", message); glDeleteProgram(p); return 0; }
  return p;
}

int main(void) {
  logs();
  fprintf(stderr, "ZER0DAY: original RPCS3 C++ core linked; game providers use Null backends.\n");
  int status = 1, user = -1, pad = -1, users_owned = 0;
  EGLDisplay display = EGL_NO_DISPLAY; EGLSurface surface = EGL_NO_SURFACE; EGLContext context = EGL_NO_CONTEXT;
  GLuint prog = 0, vao = 0, vbo = 0, texture = 0;
  zd_catalog *catalog = NULL, *pending = NULL; zd_scanner *scan = NULL; uint32_t *pixels = NULL;
  zd_ui ui; memset(&ui, 0, sizeof(ui));
  int user_rc = sceUserServiceInitialize(NULL); if (user_rc >= 0) users_owned = 1;
  if (sceUserServiceGetInitialUser(&user) < 0 || scePadInit() < 0 || (pad = scePadOpen(user, 0, 0, NULL)) < 0) { fprintf(stderr, "Controller initialization failed for initial user.\n"); goto cleanup; }
  if (!zd_render_init("/app0/assets/font.zdf")) { fprintf(stderr, "Font asset could not be loaded.\n"); goto cleanup; }
  display = eglGetDisplay(EGL_DEFAULT_DISPLAY); if (display == EGL_NO_DISPLAY) goto egl_failure;
  eglSetDisplayModePS5(display, 1920, 1080); eglSetDisplayRefreshPS5(display, 60);
  if (!eglInitialize(display, NULL, NULL) || !eglBindAPI(EGL_OPENGL_API)) goto egl_failure;
  const EGLint config_attrs[] = {EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
  EGLConfig config; EGLint configs = 0;
  if (!eglChooseConfig(display, config_attrs, &config, 1, &configs) || configs < 1) goto egl_failure;
  surface = eglCreateWindowSurface(display, config, (EGLNativeWindowType)0, NULL);
  const EGLint context_attrs[] = {EGL_CONTEXT_MAJOR_VERSION,3,EGL_CONTEXT_MINOR_VERSION,3,EGL_CONTEXT_OPENGL_PROFILE_MASK,EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,EGL_NONE};
  context = eglCreateContext(display, config, EGL_NO_CONTEXT, context_attrs);
  if (surface == EGL_NO_SURFACE || context == EGL_NO_CONTEXT || !eglMakeCurrent(display, surface, surface, context)) goto egl_failure;
  if (!eglSwapInterval(display, 1)) { fprintf(stderr, "EGL swap interval failed.\n"); goto cleanup; }
  prog = program(); if (!prog) goto cleanup;
  const GLfloat vertices[] = {-1,-1,0,1,1,-1,1,1,-1,1,0,0,1,1,1,0};
  glGenVertexArrays(1,&vao); glBindVertexArray(vao); glGenBuffers(1,&vbo); glBindBuffer(GL_ARRAY_BUFFER,vbo);
  glBufferData(GL_ARRAY_BUFFER,sizeof(vertices),vertices,GL_STATIC_DRAW); glEnableVertexAttribArray(0);
  glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,4*sizeof(GLfloat),(const void *)0); glEnableVertexAttribArray(1);
  glVertexAttribPointer(1,2,GL_FLOAT,GL_FALSE,4*sizeof(GLfloat),(const void *)(2*sizeof(GLfloat)));
  glUseProgram(prog); glUniform1i(glGetUniformLocation(prog,"tex"),0); glGenTextures(1,&texture); glActiveTexture(GL_TEXTURE0); glBindTexture(GL_TEXTURE_2D,texture);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE); glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
  glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1280,720,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL); glViewport(0,0,1920,1080);
  catalog = calloc(1,sizeof(*catalog)); pending = calloc(1,sizeof(*pending)); pixels = malloc(1280*720*sizeof(*pixels));
  if (!catalog || !pending || !pixels) { fprintf(stderr, "UI allocation failed.\n"); goto cleanup; }
  const char *roots[] = {"/mnt/usb0","/mnt/usb1","/mnt/usb2","/mnt/usb3","/mnt/usb4","/mnt/usb5","/mnt/usb6","/mnt/usb7"};
  unsigned char sample[1024] __attribute__((aligned(16))); uint32_t previous = 0; uint64_t last_scan = 0, next_repeat = 0, notice_until = 0;
  int dirty = 1, last_direction = 0, running = 1, was_connected = 0; char notice[160] = {0};
  if (!zd_core_initialize(notice,sizeof(notice))) { fprintf(stderr,"Core initialization: %s\n",notice); notice_until = sceKernelGetProcessTime()+10000000; }
  while (running) {
    zd_core_poll(); uint64_t now = sceKernelGetProcessTime(); memset(sample,0,sizeof(sample)); zd_pad state = {0,0,128,128};
    if (scePadReadState(pad,sample) >= 0) state = zd_pad_decode(sample,sizeof(sample));
    if ((int)state.connected != was_connected) { was_connected = (int)state.connected; dirty = 1; }
    uint32_t pressed = state.buttons & ~previous; previous = state.buttons; int direction = 0;
    if (state.connected) { if ((state.buttons&0x80)||state.lx<72) direction=ZD_LEFT; else if ((state.buttons&0x20)||state.lx>184) direction=ZD_RIGHT; else if ((state.buttons&0x10)||state.ly<72) direction=ZD_UP; else if ((state.buttons&0x40)||state.ly>184) direction=ZD_DOWN; }
    if (direction && (direction != last_direction || now >= next_repeat)) { zd_ui_move(&ui,catalog,direction); next_repeat = now + (direction != last_direction ? 350000 : 130000); dirty = 1; }
    last_direction = direction;
    if (pressed&0x400) { zd_ui_move(&ui,catalog,ZD_PREV); dirty=1; }
    if (pressed&0x800) { zd_ui_move(&ui,catalog,ZD_NEXT); dirty=1; }
    if ((pressed&0x1000)&&!scan) { last_scan=0; dirty=1; }
    if ((pressed&0x8)&&(state.buttons&0x2000)) running=0;
    if (pressed&0x4000) {
      zd_intent intent=zd_ui_capture(&ui,catalog); int valid=zd_ui_validate(&intent,catalog); const zd_game *chosen=NULL;
      for (unsigned i=0;i<catalog->count;++i) if (!strcmp(intent.key,catalog->games[i].key)) { chosen=&catalog->games[i]; break; }
      valid = valid && chosen && zd_game_revalidate(chosen);
      if (valid) zd_core_boot(chosen->eboot,chosen->title_id,notice,sizeof(notice)); else snprintf(notice,sizeof(notice),"%s","Il gioco non è disponibile. Aggiorna la libreria.");
      notice_until=now+5000000; dirty=1;
    }
    if (!scan && (!last_scan || now-last_scan>=4000000)) { scan=zd_scan_begin(pending,roots,sizeof(roots)/sizeof(roots[0])); last_scan=now; dirty=1; if(!scan){snprintf(notice,sizeof(notice),"Impossibile avviare la scansione USB.");notice_until=now+5000000;} }
    if (scan && zd_scan_step(scan,12)) { zd_scan_end(scan); scan=NULL; zd_catalog *old=catalog; catalog=pending; pending=old; zd_ui_refresh(&ui,catalog); dirty=1; fprintf(stderr,"Catalog: %u games, %u USB, %u warnings, limited=%u\n",catalog->count,catalog->mounts,catalog->warnings,catalog->limited); }
    if (notice_until && now>=notice_until) { notice[0]=0; notice_until=0; dirty=1; }
    if (dirty) { const char *message=state.connected?notice:"Controller scollegato: ricollegalo per navigare."; if(!zd_render(pixels,1280,720,&ui,catalog,scan!=NULL,0,message)) goto cleanup; glTexSubImage2D(GL_TEXTURE_2D,0,0,0,1280,720,GL_RGBA,GL_UNSIGNED_BYTE,pixels); dirty=0; }
    glDrawArrays(GL_TRIANGLE_STRIP,0,4); if(glGetError()!=GL_NO_ERROR){fprintf(stderr,"OpenGL presentation failed.\n");goto cleanup;} if(!eglSwapBuffers(display,surface)) goto egl_failure;
  }
  status=0; goto cleanup;
egl_failure:
  fprintf(stderr,"EGL initialization/presentation failed: 0x%x\n",eglGetError());
cleanup:
  zd_core_shutdown(); zd_scan_end(scan); free(catalog); free(pending); free(pixels); zd_render_shutdown();
  if(context!=EGL_NO_CONTEXT){ if(texture)glDeleteTextures(1,&texture); if(vbo)glDeleteBuffers(1,&vbo); if(vao)glDeleteVertexArrays(1,&vao); if(prog)glDeleteProgram(prog); eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT); eglDestroyContext(display,context); }
  if(surface!=EGL_NO_SURFACE)eglDestroySurface(display,surface); if(display!=EGL_NO_DISPLAY)eglTerminate(display); if(pad>=0)scePadClose(pad); if(users_owned)sceUserServiceTerminate(); return status;
}
