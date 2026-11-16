import React, { useMemo, useRef, useState } from "react";
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import Decimal from "decimal.js";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";
import { useApp, newKey } from "./context";
import {
  assistant,
  cartTotal,
  decimalInput,
  effectiveInventory,
  kindLabel,
  localDay,
  mayDiscard,
  money,
  normalize,
  preparedPortions,
  quantity,
  saleCommand,
} from "./domain";
import {
  Button,
  C,
  Card,
  Chip,
  Empty,
  Field,
  Icon,
  Label,
  Note,
  s,
  Title,
} from "./ui";
import type { Ingredient, QueueItem } from "./types";
import { SERVER } from "./api";

export type Route =
  | "home"
  | "inventory"
  | "pos"
  | "assistant"
  | "sync"
  | "receipt"
  | "issue"
  | "account";
type Go = (route: Route) => void;
const errorMessage = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "No se pudo completar. Intenta nuevamente.";
const stamp = (date: string) =>
  new Date(date).toLocaleString("es-MX", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

export function Login() {
  const app = useApp();
  const [email, setEmail] = useState(app.session?.user.email || ""),
    [password, setPassword] = useState(""),
    [show, setShow] = useState(false),
    [error, setError] = useState("");
  async function submit() {
    setError("");
    if (!email.trim() || !password) {
      setError("Captura tu correo y contraseña.");
      return;
    }
    try {
      await app.login(email, password);
      setPassword("");
    } catch (e) {
      setError(errorMessage(e));
    }
  }
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: C.green }}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ flexGrow: 1 }}
        >
          <LinearGradient
            colors={[C.greenDark, C.green]}
            style={{ padding: 30, paddingTop: 28, paddingBottom: 36, gap: 22 }}
          >
            <View style={s.between}>
              <Text
                style={{
                  color: C.gold,
                  fontSize: 11,
                  letterSpacing: 3,
                  fontWeight: "700",
                }}
              >
                SAN JUAN DEL RÍO
              </Text>
              <Icon name="leaf-outline" color={C.gold} size={26} />
            </View>
            <Text
              style={{
                fontFamily: Platform.OS === "ios" ? "Georgia" : "serif",
                color: C.white,
                fontSize: 44,
                letterSpacing: 3,
              }}
            >
              CORTIJO <Text style={{ color: C.gold }}>7</Text>
            </Text>
            <Text style={{ color: "#DDE7DF", fontSize: 19, lineHeight: 28 }}>
              Tu operación, contigo.{`\n`}Incluso sin conexión.
            </Text>
            <View style={s.row}>
              <View style={{ width: 24, height: 1, backgroundColor: C.gold }} />
              <Text
                style={{ color: "#BBCDBF", fontSize: 10, letterSpacing: 2 }}
              >
                ALMACÉN · COCINA · VENTAS
              </Text>
            </View>
          </LinearGradient>
          <View
            style={{
              flex: 1,
              backgroundColor: C.cream,
              borderTopLeftRadius: 30,
              borderTopRightRadius: 30,
              marginTop: -15,
              padding: 28,
              gap: 22,
            }}
          >
            <View>
              <Text style={[s.eyebrow, { marginBottom: 10 }]}>
                BIENVENIDO A TU ESPACIO
              </Text>
              <Text style={s.title}>
                {app.needsLogin ? "Renueva tu acceso." : "Todo en su lugar."}
              </Text>
              <Text style={[s.muted, { marginTop: 10 }]}>
                Ingresa con el mismo usuario de la web.
                {app.needsLogin
                  ? " Tus pendientes siguen guardados en el teléfono."
                  : " Descarga tus datos una vez y llévalos contigo."}
              </Text>
            </View>
            <Field
              label="Correo electrónico"
              value={email}
              onChangeText={setEmail}
              placeholder="tu@correo.com"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              textContentType="username"
              autoComplete="email"
            />
            <View style={{ gap: 8 }}>
              <Label>Contraseña</Label>
              <View style={{ position: "relative" }}>
                <TextInput
                  accessibilityLabel="Contraseña"
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!show}
                  textContentType="password"
                  autoComplete="current-password"
                  autoCapitalize="none"
                  style={[s.input, { paddingRight: 56 }]}
                  onSubmitEditing={submit}
                />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={
                    show ? "Ocultar contraseña" : "Mostrar contraseña"
                  }
                  onPress={() => setShow(!show)}
                  hitSlop={10}
                  style={{ position: "absolute", right: 16, top: 15 }}
                >
                  <Icon name={show ? "eye-off-outline" : "eye-outline"} />
                </Pressable>
              </View>
            </View>
            {!!error && <Note warning>{error}</Note>}
            <Button
              title="Entrar a Cortijo 7"
              onPress={submit}
              icon="arrow-forward"
              loading={app.busy}
            />
            <Note>
              El primer acceso necesita internet. Después podrás consultar y
              capturar sin conexión hasta el vencimiento de tu sesión.
            </Note>
            <Text style={[s.tiny, { textAlign: "center" }]}>
              Acceso personal · Sin cuentas nuevas ni contraseñas compartidas
              {`\n`}Tus permisos se mantienen en web y móvil.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Page({
  children,
  refresh = true,
}: {
  children: React.ReactNode;
  refresh?: boolean;
}) {
  const app = useApp();
  return (
    <ScrollView
      keyboardShouldPersistTaps="handled"
      refreshControl={
        refresh ? (
          <RefreshControl
            refreshing={app.busy}
            onRefresh={app.sync}
            tintColor={C.green}
          />
        ) : undefined
      }
      contentContainerStyle={s.content}
    >
      {children}
    </ScrollView>
  );
}
function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentProps<typeof Icon>["name"];
}) {
  return (
    <Card style={{ flex: 1, minWidth: 135, gap: 8, padding: 16 }}>
      <Icon name={icon} size={20} color={C.muted} />
      <Text
        style={{
          fontSize: 27,
          letterSpacing: -1,
          fontWeight: "700",
          color: C.green,
        }}
      >
        {value}
      </Text>
      <Text style={s.tiny}>{label}</Text>
    </Card>
  );
}
export function Home({ go }: { go: Go }) {
  const app = useApp(),
    data = app.snapshot!;
  const rows = effectiveInventory(data),
    low = rows.filter((i) => new Decimal(i.available).lte(i.minimum));
  const pending = app.queue.filter((i) => i.status !== "confirmed").length;
  const today = localDay(),
    sales = data.sales.filter(
      (s) => !s.cancelled && localDay(new Date(s.created_at)) === today,
    );
  const expiryEnd = new Date(today + "T12:00:00Z");
  expiryEnd.setUTCDate(expiryEnd.getUTCDate() + data.expiry_alert_days);
  const attention = data.lots.filter(
    (l) => l.expires_on && l.expires_on <= expiryEnd.toISOString().slice(0, 10),
  );
  return (
    <Page>
      <View>
        <Text style={s.eyebrow}>UN BUEN DÍA COMIENZA EN ORDEN</Text>
        <Text style={[s.title, { marginTop: 10 }]}>
          Hola, {app.session!.user.name.split(" ")[0]}.
        </Text>
        <Text style={[s.muted, { marginTop: 7 }]}>
          Lo que necesita tu atención, en un vistazo.
        </Text>
      </View>
      <LinearGradient
        colors={[C.green, "#28594A"]}
        style={{ padding: 24, borderRadius: 22, gap: 16 }}
      >
        <View style={s.between}>
          <Text
            style={{
              color: "#C7D8CD",
              fontSize: 10,
              fontWeight: "800",
              letterSpacing: 2,
            }}
          >
            PULSO DE TU OPERACIÓN
          </Text>
          <Icon name="pulse-outline" color={C.gold} />
        </View>
        <Text
          style={{
            color: C.white,
            fontSize: 26,
            lineHeight: 33,
            letterSpacing: -0.6,
          }}
        >
          {pending
            ? `${pending} operaciones listas\npara conectar con la web.`
            : low.length
              ? `${low.length} ingredientes\nnecesitan reposición.`
              : "Tu restaurante,\nun poco más en orden."}
        </Text>
        <Text style={{ color: "#D6E3D8", lineHeight: 20, fontSize: 12 }}>
          Datos descargados: {stamp(data.server_time)}. Desliza hacia abajo para
          actualizar.
        </Text>
        <Pressable
          accessibilityRole="button"
          onPress={() => go(pending ? "sync" : "assistant")}
          style={s.row}
        >
          <Text style={{ color: C.gold, fontWeight: "700", fontSize: 13 }}>
            {pending ? "Revisar pendientes" : "Pregúntale a C7"}
          </Text>
          <Icon name="arrow-forward" color={C.gold} size={18} />
        </Pressable>
      </LinearGradient>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
        {rows.length > 0 && (
          <>
            <Stat
              label="INGREDIENTES ACTIVOS"
              value={String(rows.length)}
              icon="leaf-outline"
            />
            <Stat
              label="LOTES A REVISAR"
              value={String(attention.length)}
              icon="time-outline"
            />
          </>
        )}
        {data.user.permissions.includes("sales.read") && (
          <Stat
            label="VENTAS DE HOY DESCARGADAS"
            value={money(
              sales.reduce((s, sale) => s.add(sale.total), new Decimal(0)),
            )}
            icon="receipt-outline"
          />
        )}
      </View>
      <View style={s.between}>
        <Text style={s.h2}>Tu siguiente movimiento</Text>
        <Icon name="arrow-down-outline" size={17} color={C.muted} />
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
        {data.user.permissions.includes("inventory.write") && (
          <>
            <Action
              title="Recibir mercancía"
              sub="Una compra, varios lotes"
              icon="download-outline"
              onPress={() => go("receipt")}
            />
            <Action
              title="Registrar salida"
              sub="Consumo por PEPS"
              icon="arrow-up-outline"
              onPress={() => go("issue")}
            />
          </>
        )}
        {data.user.permissions.includes("sales.write") && (
          <Action
            title="Nueva venta"
            sub="Tus productos y recetas"
            icon="storefront-outline"
            onPress={() => go("pos")}
          />
        )}
        <Action
          title="Asistente C7"
          sub="Respuestas, incluso offline"
          icon="sparkles-outline"
          onPress={() => go("assistant")}
        />
      </View>
      {!!low.length && (
        <Card>
          <Text style={s.h2}>Por debajo del mínimo</Text>
          {low.slice(0, 4).map((i) => (
            <View key={i.id} style={s.between}>
              <Text style={[s.body, { flex: 1 }]}>{i.name}</Text>
              <Text style={{ color: C.clay, fontWeight: "700" }}>
                {quantity(i.available)} {i.unit}
              </Text>
            </View>
          ))}
          <Button
            title="Ver mi lista de reposición"
            secondary
            onPress={() => go("assistant")}
            icon="sparkles-outline"
          />
        </Card>
      )}
      <Text style={s.tiny}>
        Las ventas de hoy corresponden a los registros descargados más
        recientes. Los pendientes se contabilizan cuando Render los confirma.
      </Text>
    </Page>
  );
}
function Action({
  title,
  sub,
  icon,
  onPress,
}: {
  title: string;
  sub: string;
  icon: React.ComponentProps<typeof Icon>["name"];
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        s.card,
        {
          flex: 1,
          minWidth: 140,
          gap: 9,
          padding: 17,
          opacity: pressed ? 0.7 : 1,
        },
      ]}
    >
      <View
        style={{
          backgroundColor: C.pale,
          borderRadius: 12,
          padding: 11,
          alignSelf: "flex-start",
        }}
      >
        <Icon name={icon} />
      </View>
      <Text style={{ fontSize: 15, color: C.ink, fontWeight: "700" }}>
        {title}
      </Text>
      <Text style={s.tiny}>{sub}</Text>
    </Pressable>
  );
}

export function Inventory({ go }: { go: Go }) {
  const { snapshot: data, busy, sync } = useApp();
  const [search, setSearch] = useState(""),
    [category, setCategory] = useState("Todos"),
    [selected, setSelected] = useState<number | null>(null);
  const rows = effectiveInventory(data!),
    categories = [
      "Todos",
      "Bajo mínimo",
      ...new Set(rows.map((i) => i.category)),
    ];
  const filtered = rows.filter(
    (i) =>
      normalize(`${i.name} ${i.code || ""}`).includes(normalize(search)) &&
      (category === "Todos" ||
        (category === "Bajo mínimo"
          ? new Decimal(i.available).lte(i.minimum)
          : i.category === category)),
  );
  const item = selected ? rows.find((i) => i.id === selected) : undefined;
  if (item)
    return (
      <Page>
        <Button
          title="Volver al inventario"
          secondary
          icon="arrow-back"
          onPress={() => setSelected(null)}
        />
        <Title sub={`${item.category} · Unidad base: ${item.unit}`}>
          {item.name}
        </Title>
        <View style={s.row}>
          <Stat
            label="DISPONIBLE DESCARGADO"
            value={quantity(item.available)}
            icon="cube-outline"
          />
          <Stat
            label="MÍNIMO"
            value={quantity(item.minimum)}
            icon="trending-down-outline"
          />
        </View>
        <Note>
          Existencia consultada al {stamp(data!.server_time)}. Los lotes
          caducados se excluyen al calcular disponibilidad.
        </Note>
        <Text style={s.h2}>Lotes en orden PEPS</Text>
        {data!.lots
          .filter((l) => l.ingredient_id === item.id)
          .map((l, index) => (
            <Card key={l.id}>
              <View style={s.between}>
                <Text style={s.h2}>
                  {String(index + 1).padStart(2, "0")} ·{" "}
                  {l.code || `Lote ${l.id}`}
                </Text>
                <Text style={{ fontWeight: "700", color: C.green }}>
                  {quantity(l.quantity)} {item.unit}
                </Text>
              </View>
              <Text style={s.muted}>
                Entrada: {stamp(l.received_at)}
                {`\n`}
                {l.expires_on
                  ? `Caducidad: ${l.expires_on}`
                  : "Caducidad sin registrar"}
              </Text>
              {l.expires_on && l.expires_on < localDay() && (
                <Chip label="Caducado · no disponible" />
              )}
            </Card>
          ))}
        {!data!.lots.some((l) => l.ingredient_id === item.id) && (
          <Empty
            title="Sin lotes disponibles"
            description="Las entradas confirmadas aparecerán aquí."
          />
        )}
        <Button
          title="Registrar salida"
          secondary
          onPress={() => go("issue")}
        />
      </Page>
    );
  return (
    <FlatList
      data={filtered}
      keyExtractor={(i) => String(i.id)}
      contentContainerStyle={s.content}
      refreshControl={
        <RefreshControl
          refreshing={busy}
          onRefresh={sync}
          tintColor={C.green}
        />
      }
      ListHeaderComponent={
        <View style={{ gap: 18, marginBottom: 18 }}>
          <Title sub="Existencias y trazabilidad, contigo.">
            Tu inventario.
          </Title>
          <Field
            label="Buscar ingrediente o código"
            placeholder="Ej. aguacate, leche…"
            value={search}
            onChangeText={setSearch}
          />
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: 8 }}
          >
            {categories.map((c) => (
              <Chip
                key={c}
                label={c}
                active={category === c}
                onPress={() => setCategory(c)}
              />
            ))}
          </ScrollView>
          <Text style={s.tiny}>
            {filtered.length} ingredientes · Descarga {stamp(data!.server_time)}
          </Text>
        </View>
      }
      ListEmptyComponent={
        <Empty
          title="Sin resultados"
          description="Prueba otro nombre o actualiza los datos."
        />
      }
      renderItem={({ item: i }) => {
        const low = new Decimal(i.available).lte(i.minimum);
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Ver ${i.name}`}
            onPress={() => setSelected(i.id)}
            style={[s.card, { marginBottom: 10, padding: 17 }]}
          >
            <View style={s.between}>
              <View style={[s.row, { flex: 1 }]}>
                <View
                  style={{
                    padding: 11,
                    backgroundColor: low ? "#FAF0DF" : C.pale,
                    borderRadius: 13,
                  }}
                >
                  <Icon name="leaf-outline" color={low ? C.amber : C.green} />
                </View>
                <View style={{ flex: 1, gap: 5 }}>
                  <Text style={[s.body, { fontWeight: "700" }]}>{i.name}</Text>
                  <Text style={s.tiny}>
                    {i.category}
                    {i.code ? " · " + i.code : ""}
                  </Text>
                </View>
              </View>
              <View style={{ alignItems: "flex-end", gap: 5 }}>
                <Text
                  style={{
                    color: low ? C.clay : C.green,
                    fontWeight: "700",
                    fontSize: 19,
                  }}
                >
                  {quantity(i.available)}
                </Text>
                <Text style={s.tiny}>
                  {i.unit} {low ? "· bajo mínimo" : "disponible"}
                </Text>
              </View>
            </View>
          </Pressable>
        );
      }}
    />
  );
}

export function POS({ go }: { go: Go }) {
  const app = useApp(),
    data = app.snapshot!,
    [search, setSearch] = useState(""),
    [cart, setCart] = useState<Record<number, number>>({}),
    [method, setMethod] = useState<"cash" | "card" | "transfer">("cash"),
    [received, setReceived] = useState(""),
    [saving, setSaving] = useState(false);
  const validCart = Object.fromEntries(
    Object.entries(cart).filter(([id]) =>
      data.products.some((p) => p.id === Number(id)),
    ),
  );
  const total = cartTotal(data.products, validCart),
    rows = effectiveInventory(data);
  const saveLock = useRef(false);
  function change(id: number, delta: number) {
    setCart((current) => {
      const next = { ...current };
      next[id] = Math.min(9999, (next[id] || 0) + delta);
      if (next[id] <= 0) delete next[id];
      return next;
    });
  }
  async function save() {
    if (saveLock.current) return;
    saveLock.current = true;
    setSaving(true);
    try {
      const command = saleCommand(
        newKey(),
        data.products,
        validCart,
        method,
        received,
      );
      await app.enqueue(
        command,
        `${Object.values(validCart).reduce((a, b) => a + b, 0)} productos · ${money(total)}`,
      );
      setCart({});
      setReceived("");
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert(
        "Venta guardada en el teléfono",
        "Consulta su estado y folio en Sincronización. El cobro y el inventario se confirman cuando Render valida la operación.",
        [{ text: "Ver estado", onPress: () => go("sync") }],
      );
    } catch (e) {
      Alert.alert("Revisa tu venta", errorMessage(e));
    } finally {
      setSaving(false);
      saveLock.current = false;
    }
  }
  return (
    <Page>
      <Title sub="Una venta conecta cocina e inventario.">
        Punto de venta.
      </Title>
      <Field
        label="Buscar producto"
        value={search}
        onChangeText={setSearch}
        placeholder="Platillo, bebida o código"
      />
      {data.products
        .filter((p) =>
          normalize(`${p.name} ${p.code || ""}`).includes(normalize(search)),
        )
        .map((p) => {
          const portions = preparedPortions(p, rows);
          return (
            <Card key={p.id} style={{ padding: 17 }}>
              <View style={s.between}>
                <View style={{ flex: 1, gap: 5 }}>
                  <Text style={s.tiny}>{p.category.toUpperCase()}</Text>
                  <Text style={[s.body, { fontWeight: "700" }]}>{p.name}</Text>
                  <Text
                    style={{ fontSize: 17, color: C.green, fontWeight: "700" }}
                  >
                    {money(p.price)}
                  </Text>
                  {portions !== null && (
                    <Text style={s.tiny}>
                      Hasta {portions} porciones según la descarga
                    </Text>
                  )}
                </View>
                <View style={s.row}>
                  {cart[p.id] ? (
                    <>
                      <Pressable
                        accessibilityRole="button"
                        accessibilityLabel={`Quitar ${p.name}`}
                        onPress={() => change(p.id, -1)}
                        hitSlop={9}
                        style={{
                          padding: 10,
                          backgroundColor: C.pale,
                          borderRadius: 10,
                        }}
                      >
                        <Icon name="remove" size={18} />
                      </Pressable>
                      <Text style={s.h2}>{cart[p.id]}</Text>
                    </>
                  ) : null}
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Agregar ${p.name}`}
                    onPress={() => change(p.id, 1)}
                    style={{
                      padding: 10,
                      backgroundColor: C.green,
                      borderRadius: 10,
                    }}
                  >
                    <Icon name="add" color={C.white} size={18} />
                  </Pressable>
                </View>
              </View>
            </Card>
          );
        })}
      {!data.products.length && (
        <Empty
          title="El menú está por comenzar"
          description="Configura productos y recetas en la web y sincroniza."
          icon="restaurant-outline"
        />
      )}
      {!!Object.keys(validCart).length && (
        <Card style={{ borderColor: C.green, borderWidth: 1.5 }}>
          <View style={s.between}>
            <Text style={s.h2}>Tu carrito</Text>
            <Text style={{ fontSize: 26, color: C.green, fontWeight: "700" }}>
              {money(total)}
            </Text>
          </View>
          {Object.entries(validCart).map(([id, count]) => {
            const p = data.products.find((p) => p.id === Number(id))!;
            return (
              <Text key={id} style={s.body}>
                {count} × {p.name} · {money(new Decimal(p.price).mul(count))}
              </Text>
            );
          })}
          <View style={s.line} />
          <Label>Forma de pago registrada</Label>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {(["cash", "card", "transfer"] as const).map((m) => (
              <Chip
                key={m}
                label={
                  {
                    cash: "Efectivo",
                    card: "Tarjeta",
                    transfer: "Transferencia",
                  }[m]
                }
                active={method === m}
                onPress={() => setMethod(m)}
              />
            ))}
          </View>
          {method === "cash" && (
            <Field
              label="Efectivo recibido · MXN"
              value={received}
              onChangeText={setReceived}
              keyboardType="decimal-pad"
              placeholder="0.00"
            />
          )}
          <Note warning>
            Sin conexión, esta venta queda pendiente. Se revisan existencias,
            precios y versión de receta al sincronizar. La app registra el
            método de pago; no hace cargos bancarios.
          </Note>
          <Button
            title="Guardar venta para sincronizar"
            onPress={save}
            loading={saving}
            icon="cloud-upload-outline"
          />
        </Card>
      )}
    </Page>
  );
}

export function Assistant({ go }: { go: Go }) {
  const app = useApp(),
    data = app.snapshot!,
    [input, setInput] = useState("");
  const [messages, setMessages] = useState<
    {
      id: string;
      text: string;
      own: boolean;
      action?: Route;
      actionLabel?: string;
    }[]
  >([{ id: "hello", ...assistant("hola", data, app.queue), own: false }]);
  const scroll = useRef<React.ElementRef<typeof ScrollView>>(null);
  function send(text = input) {
    if (!text.trim()) return;
    const result = assistant(text.trim(), data, app.queue);
    setMessages((current) => [
      ...current.slice(-39),
      { id: newKey(), text: text.trim(), own: true },
      { id: newKey(), ...result, own: false },
    ]);
    setInput("");
    void Haptics.selectionAsync();
  }
  const prompts = data.ingredients.length
    ? [
        "¿Qué debo comprar?",
        "¿Qué está por caducar?",
        "¿Qué puedo preparar?",
        "Mis pendientes",
      ]
    : ["Mis ventas de hoy", "Mis pendientes", "¿Cómo funcionas sin internet?"];
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={{ flex: 1 }}
    >
      <ScrollView
        ref={scroll}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={() =>
          scroll.current?.scrollToEnd({ animated: true })
        }
        contentContainerStyle={s.content}
      >
        <View style={s.row}>
          <View
            style={{
              width: 54,
              height: 54,
              backgroundColor: C.green,
              borderRadius: 19,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Icon name="sparkles" color={C.gold} size={27} />
          </View>
          <View>
            <Text style={s.h2}>C7 · Tu asistente</Text>
            <Text style={s.tiny}>Analiza tus datos · También sin conexión</Text>
          </View>
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {prompts.map((p) => (
            <Chip key={p} label={p} onPress={() => send(p)} />
          ))}
        </View>
        {messages.map((m) => (
          <View
            key={m.id}
            style={{
              maxWidth: "95%",
              alignSelf: m.own ? "flex-end" : "flex-start",
              backgroundColor: m.own ? C.green : C.white,
              padding: 18,
              borderRadius: 19,
              borderTopRightRadius: m.own ? 4 : 19,
              borderTopLeftRadius: m.own ? 19 : 4,
              borderWidth: m.own ? 0 : 1,
              borderColor: C.border,
              gap: 12,
            }}
          >
            {!m.own && <Text style={[s.eyebrow, { color: C.clay }]}>C7</Text>}
            <Text
              selectable
              style={[s.body, { color: m.own ? C.white : C.ink }]}
            >
              {m.text}
            </Text>
            {m.action && (
              <Button
                secondary
                title={m.actionLabel || "Abrir"}
                onPress={() => go(m.action!)}
                icon="arrow-forward"
              />
            )}
          </View>
        ))}
        <Text style={s.tiny}>
          Asistente de reglas y cálculos locales; no envía tus consultas a
          servicios externos ni ejecuta cambios desde el chat.
        </Text>
      </ScrollView>
      <View
        style={[
          s.row,
          {
            padding: 16,
            paddingTop: 10,
            backgroundColor: C.cream,
            borderTopWidth: 1,
            borderColor: C.border,
          },
        ]}
      >
        <TextInput
          accessibilityLabel="Pregunta al asistente C7"
          placeholder="Pregunta por tu operación…"
          placeholderTextColor={C.muted}
          value={input}
          onChangeText={setInput}
          maxLength={500}
          style={[s.input, { flex: 1 }]}
          onSubmitEditing={() => send()}
          returnKeyType="send"
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Enviar pregunta"
          onPress={() => send()}
          style={{ backgroundColor: C.green, padding: 15, borderRadius: 14 }}
        >
          <Icon name="arrow-up" color={C.white} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

export function SyncScreen() {
  const app = useApp();
  const pending = app.queue.filter((i) => i.status !== "confirmed");
  function remove(item: QueueItem) {
    Alert.alert(
      "Descartar operación local",
      "Se retirará esta captura. Si necesitas corregirla, crea otra después de revisar los datos actualizados.",
      [
        { text: "Conservar", style: "cancel" },
        {
          text: "Descartar",
          style: "destructive",
          onPress: () => {
            app
              .discard(item)
              .catch((e) =>
                Alert.alert("No se pudo descartar", errorMessage(e)),
              );
          },
        },
      ],
    );
  }
  return (
    <Page>
      <Title sub="Tu teléfono y la web, en el mismo equipo.">
        Sincronización.
      </Title>
      <Card style={{ backgroundColor: C.green }}>
        <View style={s.between}>
          <Icon
            name={app.online ? "cloud-done-outline" : "cloud-offline-outline"}
            color={C.gold}
            size={32}
          />
          <Text style={{ color: C.gold, fontWeight: "700", fontSize: 13 }}>
            {app.busy
              ? "CONECTANDO"
              : app.online
                ? "CON CONEXIÓN"
                : "MODO LOCAL"}
          </Text>
        </View>
        <Text style={{ color: C.white, fontSize: 25, fontWeight: "700" }}>
          {pending.length} operaciones pendientes
        </Text>
        <Text style={{ color: "#D3DED4", lineHeight: 21 }}>
          {app.message ||
            "Los registros se envían en orden y conservan la misma referencia en cada reintento."}
        </Text>
      </Card>
      <Button
        title="Sincronizar ahora"
        icon="sync-outline"
        loading={app.busy}
        onPress={app.sync}
      />
      <Note>
        Las operaciones se validan completas y en orden. Un conflicto detiene
        los registros siguientes hasta que lo revises. No se descartan capturas
        por perder conexión.
      </Note>
      {app.queue.length ? (
        [...app.queue]
          .sort(
            (a, b) =>
              (a.status === "confirmed" ? 1 : 0) -
                (b.status === "confirmed" ? 1 : 0) ||
              a.created_at.localeCompare(b.created_at),
          )
          .map((item) => (
            <Card key={item.key}>
              <View style={s.between}>
                <Text style={s.h2}>{kindLabel(item.command.kind)}</Text>
                <Chip
                  label={
                    {
                      pending: "Pendiente",
                      conflict: "Requiere revisión",
                      confirmed: "Confirmada",
                    }[item.status]
                  }
                  active={item.status === "confirmed"}
                />
              </View>
              <Text style={s.body}>{item.label}</Text>
              <Text style={s.tiny}>
                Captura: {stamp(item.created_at)}
                {`\n`}Referencia: {item.key}
              </Text>
              {item.result_id && (
                <Text selectable style={s.tiny}>
                  Folio en la web: {item.result_id}
                </Text>
              )}
              {item.error && <Note warning>{item.error}</Note>}
              {item.attempted && item.status === "pending" && (
                <Text style={s.tiny}>
                  El resultado aún no se conoce. El reintento recuperará el
                  folio si Render ya lo guardó.
                </Text>
              )}
              {mayDiscard(item) && (
                <Button
                  secondary
                  disabled={app.busy}
                  title="Descartar captura"
                  onPress={() => remove(item)}
                />
              )}
            </Card>
          ))
      ) : (
        <Empty
          title="Todo en su lugar"
          description="Las capturas que hagas desde este teléfono aparecerán aquí, con su estado y folio."
          icon="checkmark-done-outline"
        />
      )}
      {!!app.snapshot?.operations.length && (
        <>
          <Text style={s.h2}>Últimos movimientos de la web</Text>
          {app.snapshot.operations.slice(0, 8).map((o) => (
            <View key={o.id} style={s.between}>
              <View style={{ flex: 1 }}>
                <Text style={[s.body, { fontWeight: "600" }]}>
                  {kindLabel(o.kind)}
                </Text>
                <Text style={s.tiny}>{o.reason}</Text>
              </View>
              <Text style={s.tiny}>{stamp(o.created_at)}</Text>
            </View>
          ))}
        </>
      )}
    </Page>
  );
}

export function Account() {
  const app = useApp(),
    user = app.session!.user;
  return (
    <Page>
      <Title sub="Una sola cuenta para web y móvil.">Tu espacio.</Title>
      <Card>
        <View style={s.row}>
          <View
            style={{
              backgroundColor: C.gold,
              width: 56,
              height: 56,
              borderRadius: 28,
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Text style={{ fontSize: 27, color: C.green, fontFamily: "serif" }}>
              {user.name[0]}
            </Text>
          </View>
          <View style={{ flex: 1, gap: 5 }}>
            <Text style={s.h2}>{user.name}</Text>
            <Text style={s.muted}>{user.email}</Text>
            <Text style={s.tiny}>{user.role_label}</Text>
          </View>
        </View>
      </Card>
      <Card>
        <Text style={s.h2}>Tu acceso sin conexión</Text>
        <Text style={s.body}>
          Vigente hasta{" "}
          {new Date(app.session!.expires_at).toLocaleString("es-MX")}. Después
          necesitarás internet para volver a iniciar sesión.
        </Text>
        <Text style={s.muted}>
          Las restricciones, cambios de contraseña y desactivaciones de la web
          se verifican al conectar. Protege el teléfono con su código de
          bloqueo.
        </Text>
        <Text style={s.tiny}>
          Última descarga:{" "}
          {app.snapshot ? stamp(app.snapshot.server_time) : "Pendiente"}
        </Text>
      </Card>
      <Card>
        <Text style={s.h2}>El resto de tu operación</Text>
        <Text style={s.muted}>
          La web concentra administración de usuarios, edición de catálogos y
          recetas, importación Excel, cancelaciones, ajustes, reportes y
          respaldos. Los datos confirmados desde esta app aparecen en la misma
          base.
        </Text>
        <Button
          title="Abrir Cortijo 7 web"
          secondary
          icon="open-outline"
          onPress={() => {
            Linking.openURL(SERVER).catch(() =>
              Alert.alert("Abre tu navegador", SERVER),
            );
          }}
        />
      </Card>
      <Note warning>
        Cerrar sesión necesita internet y no permite dejar operaciones sin
        resolver. Desinstalar la app elimina capturas que todavía no llegaron al
        servidor.
      </Note>
      <Button
        title="Cerrar sesión y borrar datos locales"
        secondary
        icon="log-out-outline"
        onPress={() =>
          Alert.alert(
            "Cerrar sesión",
            "Se revocará este acceso y se eliminará la copia descargada del teléfono.",
            [
              { text: "Cancelar", style: "cancel" },
              {
                text: "Cerrar sesión",
                style: "destructive",
                onPress: () => {
                  app
                    .logout()
                    .catch((e) =>
                      Alert.alert("Conservamos tu sesión", errorMessage(e)),
                    );
                },
              },
            ],
          )
        }
      />
    </Page>
  );
}
