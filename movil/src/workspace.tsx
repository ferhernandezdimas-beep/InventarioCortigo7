import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  BackHandler,
  Text,
  View,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { WebView, type WebViewMessageEvent } from "react-native-webview";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import * as Print from "expo-print";
import { useApp } from "./context";
import { request, SERVER } from "./api";
import { Button, C, Icon, Note, s } from "./ui";

export function trustedWebUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.origin === new URL(SERVER).origin && !u.username && !u.password;
  } catch {
    return false;
  }
}
const BRIDGE = `(function(){
 if(window.__c7NativeBridge) return true;
 window.__c7NativeBridge=true;
 function send(v){window.ReactNativeWebView.postMessage(JSON.stringify(v));}
 document.addEventListener('click',function(e){
  var a=e.target.closest&&e.target.closest('a');if(!a)return;
  var u=new URL(a.href,location.href);if(u.origin!==location.origin)return;
  if(u.pathname.endsWith('.xlsx')||u.pathname.endsWith('.csv')||u.pathname.endsWith('/exportar')||['csv','xlsx'].includes(u.searchParams.get('format'))){e.preventDefault();send({type:'download',path:u.pathname+u.search});}
 },true);
 window.print=function(){
  var receipt=document.querySelector('.receipt-document');
  var html=receipt?'<html><head><meta charset="utf-8"><style>body{font-family:Arial;padding:24px}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ddd}small,span{display:block}button{display:none}</style></head><body>'+receipt.outerHTML+'</body></html>':document.documentElement.outerHTML;
  send({type:'print',html:html});
 };
 return true;
})();`;

export function Workspace() {
  const app = useApp(),
    web = useRef<WebView>(null),
    [revision, setRevision] = useState(0),
    [canBack, setCanBack] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const messageLock = useRef(false);
  useFocusEffect(
    React.useCallback(() => {
      const listener = BackHandler.addEventListener("hardwareBackPress", () => {
        if (canBack) {
          web.current?.goBack();
          return true;
        }
        return false;
      });
      return () => listener.remove();
    }, [canBack]),
  );
  async function share(path: string) {
    if (messageLock.current) return;
    messageLock.current = true;
    setBusy(true);
    try {
      const doc = await request<{
        filename: string;
        mime: string;
        content: string;
      }>("/documents", app.session!.token, { path });
      const safe = doc.filename.replace(/[^a-zA-Z0-9._-]/g, "_");
      const uri = FileSystem.cacheDirectory + "c7-" + Date.now() + "-" + safe;
      await FileSystem.writeAsStringAsync(uri, doc.content, {
        encoding: FileSystem.EncodingType.Base64,
      });
      if (!(await Sharing.isAvailableAsync()))
        throw new Error(
          "El archivo se descargó, pero el dispositivo no ofrece un menú para compartir.",
        );
      await Sharing.shareAsync(uri, {
        mimeType: doc.mime,
        dialogTitle: "Guardar o compartir documento",
      });
    } catch (e) {
      Alert.alert(
        "Documento",
        e instanceof Error ? e.message : "No se pudo descargar.",
      );
    } finally {
      messageLock.current = false;
      setBusy(false);
    }
  }
  function onMessage(event: WebViewMessageEvent) {
    if (!trustedWebUrl(event.nativeEvent.url)) return;
    try {
      const value = JSON.parse(event.nativeEvent.data);
      if (
        value.type === "download" &&
        typeof value.path === "string" &&
        value.path.startsWith("/") &&
        !value.path.startsWith("//")
      )
        void share(value.path);
      else if (
        value.type === "print" &&
        typeof value.html === "string" &&
        value.html.length < 2_000_000
      ) {
        Alert.alert(
          "Imprimir documento",
          "Se abrirá el diálogo de impresión del dispositivo.",
          [
            { text: "Cancelar", style: "cancel" },
            {
              text: "Continuar",
              onPress: () => {
                Print.printAsync({ html: value.html }).catch(() =>
                  Alert.alert(
                    "Impresión",
                    "No fue posible abrir la impresión en este dispositivo.",
                  ),
                );
              },
            },
          ],
        );
      }
    } catch {}
  }
  if (!app.online)
    return (
      <View style={s.content}>
        <Icon name="cloud-offline-outline" size={38} />
        <Text style={s.title}>Tu sistema completo.</Text>
        <Note>
          Las pantallas de administración necesitan conectar con Render. Puedes
          seguir consultando y capturando desde Inicio, Inventario, Venta y el
          asistente C7 sin conexión.
        </Note>
        <Button
          title="Comprobar conexión"
          onPress={app.sync}
          loading={app.busy}
        />
      </View>
    );
  return (
    <View style={{ flex: 1 }}>
      <View style={[s.between, { padding: 10, backgroundColor: C.pale }]}>
        <Text style={[s.tiny, { flex: 1 }]}>
          Sistema completo · {app.session?.user.role_label}
        </Text>
        {canBack && (
          <Button
            secondary
            title="Atrás"
            onPress={() => web.current?.goBack()}
          />
        )}
        <Button
          secondary
          title="Inicio"
          onPress={() => {
            setError("");
            setRevision((v) => v + 1);
          }}
        />
      </View>
      {busy && (
        <View style={s.row}>
          <ActivityIndicator />
          <Text style={s.tiny}>Preparando archivo…</Text>
        </View>
      )}
      {!!error ? (
        <View style={s.content}>
          <Note warning>{error}</Note>
          <Button
            title="Volver a conectar"
            onPress={() => {
              setError("");
              setRevision((v) => v + 1);
              void app.sync();
            }}
          />
        </View>
      ) : (
        <WebView
          key={`${app.session!.user.id}:${app.session!.expires_at}:${revision}`}
          ref={web}
          source={{
            uri: SERVER + "/api/mobile/v1/web-session",
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: "access_token=" + encodeURIComponent(app.session!.token),
          }}
          originWhitelist={[new URL(SERVER).origin]}
          mixedContentMode="never"
          allowFileAccess={false}
          allowUniversalAccessFromFileURLs={false}
          javaScriptCanOpenWindowsAutomatically={false}
          setSupportMultipleWindows={false}
          cacheEnabled={false}
          startInLoadingState
          renderLoading={() => (
            <View style={{ padding: 24 }}>
              <ActivityIndicator color={C.green} />
            </View>
          )}
          injectedJavaScript={BRIDGE}
          onMessage={onMessage}
          onFileDownload={({ nativeEvent }) => {
            if (trustedWebUrl(nativeEvent.downloadUrl)) {
              const u = new URL(nativeEvent.downloadUrl);
              void share(u.pathname + u.search);
            }
          }}
          onShouldStartLoadWithRequest={(nav) => {
            if (nav.url === "about:blank") return true;
            if (!trustedWebUrl(nav.url)) return false;
            if (new URL(nav.url).pathname === "/login") {
              setError(
                "La sesión web terminó. Vuelve a conectar; tu cuenta y tus pendientes locales se conservan.",
              );
              void app.sync();
              return false;
            }
            return true;
          }}
          onNavigationStateChange={(state) => setCanBack(state.canGoBack)}
          onError={() =>
            setError(
              "No fue posible cargar el sistema. Las capturas offline permanecen en el teléfono.",
            )
          }
          onHttpError={({ nativeEvent }) => {
            if (
              nativeEvent.statusCode === 404 &&
              trustedWebUrl(nativeEvent.url) &&
              new URL(nativeEvent.url).pathname === "/api/mobile/v1/web-session"
            ) {
              setError(
                "El servidor todavía no tiene la actualización para abrir Sistema dentro de la app. Es necesario publicar el backend actualizado en Render. Tus datos y pendientes se conservan.",
              );
              return;
            }
            if (nativeEvent.statusCode >= 500)
              setError(
                "Render no pudo responder. Vuelve a intentar en un momento.",
              );
          }}
        />
      )}
    </View>
  );
}
