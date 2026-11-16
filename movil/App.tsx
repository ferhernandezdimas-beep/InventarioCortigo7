import React, { useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { AppProvider, useApp } from "./src/context";
import {
  Account,
  Assistant,
  Home,
  Inventory,
  Login,
  POS,
  SyncScreen,
  type Route,
} from "./src/screens";
import { Entry } from "./src/entry";
import { Button, C, Icon, type IconName, Note, s } from "./src/ui";

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <SafeAreaView
          style={[s.screen, { justifyContent: "center", padding: 30, gap: 22 }]}
        >
          <Icon name="leaf-outline" size={42} />
          <Text style={s.title}>Tu captura importa.</Text>
          <Text style={s.body}>
            La app necesita reiniciarse. Cierra y vuelve a abrir; los registros
            ya guardados permanecen en el teléfono. Evita desinstalarla si
            tienes pendientes.
          </Text>
        </SafeAreaView>
      );
    return this.props.children;
  }
}
function Application() {
  const app = useApp(),
    [route, setRoute] = useState<Route>("home");
  if (!app.ready)
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: C.green,
          justifyContent: "center",
          alignItems: "center",
          gap: 22,
        }}
      >
        <Text
          style={{
            color: C.gold,
            fontSize: 38,
            fontFamily: "serif",
            letterSpacing: 3,
          }}
        >
          CORTIJO 7
        </Text>
        <ActivityIndicator color={C.gold} />
      </View>
    );
  if (!app.session || app.needsLogin) return <Login />;
  if (!app.snapshot)
    return (
      <SafeAreaView
        style={[s.screen, { padding: 28, justifyContent: "center", gap: 22 }]}
      >
        <Icon name="cloud-download-outline" size={44} />
        <Text style={s.title}>Preparemos tu espacio.</Text>
        <Text style={s.body}>
          Necesitamos descargar los datos de la web una primera vez para poder
          trabajar sin conexión.
        </Text>
        {!!app.message && <Note>{app.message}</Note>}
        <Button title="Descargar datos" onPress={app.sync} loading={app.busy} />
      </SafeAreaView>
    );
  const permissions = app.session.user.permissions;
  const tabs: { route: Route; label: string; icon: IconName }[] = [
    { route: "home", label: "Inicio", icon: "grid-outline" },
    ...(permissions.includes("inventory.read")
      ? [
          {
            route: "inventory" as Route,
            label: "Inventario",
            icon: "cube-outline" as IconName,
          },
        ]
      : []),
    ...(permissions.includes("sales.write")
      ? [
          {
            route: "pos" as Route,
            label: "Venta",
            icon: "storefront-outline" as IconName,
          },
        ]
      : []),
    { route: "assistant", label: "Asistente", icon: "sparkles-outline" },
    { route: "sync", label: "Conexión", icon: "sync-outline" },
  ];
  const allowed =
    route === "inventory"
      ? permissions.includes("inventory.read")
      : route === "pos"
        ? permissions.includes("sales.write")
        : ["receipt", "issue"].includes(route)
          ? permissions.includes("inventory.write")
          : true;
  const current = allowed ? route : "home",
    pending = app.queue.filter((i) => i.status !== "confirmed").length;
  return (
    <SafeAreaView style={s.screen} edges={["top", "left", "right"]}>
      <StatusBar style="dark" />
      <View
        style={{
          paddingHorizontal: 22,
          paddingVertical: 14,
          borderBottomWidth: 1,
          borderColor: C.border,
          backgroundColor: C.cream,
        }}
      >
        <View style={s.between}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Ir al inicio"
            onPress={() => setRoute("home")}
          >
            <Text
              style={{
                fontFamily: "serif",
                fontSize: 25,
                letterSpacing: 2,
                color: C.green,
              }}
            >
              CORTIJO <Text style={{ color: "#9E865D" }}>7</Text>
            </Text>
          </Pressable>
          <View style={s.row}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Ver conexión"
              onPress={() => setRoute("sync")}
              style={[s.row, { gap: 5 }]}
            >
              <View
                style={{
                  width: 6,
                  height: 6,
                  backgroundColor: app.online ? "#61805E" : C.amber,
                  borderRadius: 3,
                }}
              />
              <Text style={s.tiny}>
                {app.busy
                  ? "Sincronizando"
                  : app.online
                    ? "Con conexión"
                    : "Sin conexión"}
              </Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Mi cuenta"
              onPress={() => setRoute("account")}
              style={{
                height: 34,
                width: 34,
                backgroundColor: C.sage,
                borderRadius: 17,
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              <Text style={{ color: C.green, fontWeight: "700" }}>
                {app.session.user.name[0]}
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
      {!app.online && (
        <Pressable
          accessibilityRole="button"
          onPress={() => setRoute("sync")}
          style={{
            paddingHorizontal: 22,
            paddingVertical: 9,
            backgroundColor: "#F0E8D7",
          }}
        >
          <Text style={{ color: C.amber, fontSize: 11 }}>
            Modo local · {pending} pendientes · Última descarga{" "}
            {new Date(app.snapshot.server_time).toLocaleDateString("es-MX")}
          </Text>
        </Pressable>
      )}
      <View style={{ flex: 1 }}>
        {current === "home" ? (
          <Home go={setRoute} />
        ) : current === "inventory" ? (
          <Inventory go={setRoute} />
        ) : current === "pos" ? (
          <POS go={setRoute} />
        ) : current === "assistant" ? (
          <Assistant go={setRoute} />
        ) : current === "sync" ? (
          <SyncScreen />
        ) : current === "receipt" || current === "issue" ? (
          <Entry key={current} kind={current} go={setRoute} />
        ) : (
          <Account />
        )}
      </View>
      <SafeAreaView
        edges={["bottom"]}
        style={{
          backgroundColor: C.white,
          borderTopWidth: 1,
          borderColor: C.border,
        }}
      >
        <View style={{ flexDirection: "row", paddingVertical: 9 }}>
          {tabs.map((tab) => {
            const active = tab.route === current;
            return (
              <Pressable
                accessibilityRole="tab"
                accessibilityState={{ selected: active }}
                key={tab.route}
                onPress={() => setRoute(tab.route)}
                style={{
                  flex: 1,
                  gap: 4,
                  alignItems: "center",
                  paddingVertical: 5,
                }}
              >
                <View style={{ position: "relative" }}>
                  <Icon
                    name={tab.icon}
                    color={active ? C.green : "#939C92"}
                    size={23}
                  />
                  {tab.route === "sync" && pending > 0 && (
                    <View
                      style={{
                        position: "absolute",
                        top: -5,
                        right: -10,
                        minWidth: 15,
                        height: 15,
                        borderRadius: 8,
                        backgroundColor: C.clay,
                        justifyContent: "center",
                        paddingHorizontal: 3,
                      }}
                    >
                      <Text
                        style={{
                          fontSize: 8,
                          fontWeight: "800",
                          color: "white",
                          textAlign: "center",
                        }}
                      >
                        {pending}
                      </Text>
                    </View>
                  )}
                </View>
                <Text
                  style={{
                    color: active ? C.green : C.muted,
                    fontWeight: active ? "700" : "400",
                    fontSize: 10,
                  }}
                >
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </SafeAreaView>
    </SafeAreaView>
  );
}
export default function App() {
  return (
    <SafeAreaProvider>
      <ErrorBoundary>
        <AppProvider>
          <Application />
        </AppProvider>
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}
