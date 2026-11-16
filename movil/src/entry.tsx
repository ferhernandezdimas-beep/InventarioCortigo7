import React, { useRef, useState } from "react";
import {
  Alert,
  FlatList,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
  KeyboardAvoidingView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as Haptics from "expo-haptics";
import { useApp, newKey } from "./context";
import {
  decimalInput,
  effectiveInventory,
  normalize,
  quantity,
} from "./domain";
import { Button, C, Card, Empty, Field, Icon, Note, s, Title } from "./ui";
import type { InventoryCommand, ReceiptLine } from "./types";
import type { Route } from "./screens";

type Choice = { id: number; label: string; detail?: string };
function Select({
  label,
  value,
  options,
  onChange,
  placeholder = "Seleccionar",
}: {
  label: string;
  value: number;
  options: Choice[];
  onChange: (id: number) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false),
    [search, setSearch] = useState("");
  const current = options.find((o) => o.id === value);
  return (
    <>
      <Text style={s.label}>{label}</Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={label}
        onPress={() => {
          setSearch("");
          setShow(true);
        }}
        style={[s.input, s.between]}
      >
        <Text
          style={{ color: current ? C.ink : C.muted, fontSize: 15, flex: 1 }}
        >
          {current?.label || placeholder}
        </Text>
        <Icon name="chevron-down" size={18} />
      </Pressable>
      <Modal
        visible={show}
        animationType="slide"
        onRequestClose={() => setShow(false)}
      >
        <SafeAreaView style={s.screen}>
          <View style={{ padding: 22, gap: 18 }}>
            <View style={s.between}>
              <Text style={s.h2}>{label}</Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Cerrar selección"
                onPress={() => setShow(false)}
                hitSlop={15}
              >
                <Icon name="close" />
              </Pressable>
            </View>
            <Field
              label="Buscar"
              value={search}
              onChangeText={setSearch}
              placeholder="Escribe un nombre…"
              autoFocus
            />
          </View>
          <FlatList
            keyboardShouldPersistTaps="handled"
            data={options.filter((o) =>
              normalize(o.label).includes(normalize(search)),
            )}
            keyExtractor={(o) => String(o.id)}
            contentContainerStyle={{ padding: 22, paddingTop: 0, gap: 8 }}
            ListEmptyComponent={
              <Empty
                title="Sin opciones"
                description="Crea los registros en la web y vuelve a sincronizar."
              />
            }
            renderItem={({ item }) => (
              <Pressable
                accessibilityRole="button"
                onPress={() => {
                  onChange(item.id);
                  setShow(false);
                }}
                style={[
                  s.card,
                  {
                    padding: 17,
                    backgroundColor: item.id === value ? C.pale : C.white,
                  },
                ]}
              >
                <View style={s.between}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.body}>{item.label}</Text>
                    {item.detail && <Text style={s.tiny}>{item.detail}</Text>}
                  </View>
                  {item.id === value && <Icon name="checkmark" />}
                </View>
              </Pressable>
            )}
          />
        </SafeAreaView>
      </Modal>
    </>
  );
}
type DraftLine = {
  id: string;
  ingredient: number;
  quantity: string;
  cost: string;
  code: string;
  expiry: string;
  presentation: number;
};
const blank = (): DraftLine => ({
  id: newKey(),
  ingredient: 0,
  quantity: "",
  cost: "",
  code: "",
  expiry: "",
  presentation: 0,
});
export function Entry({
  kind,
  go,
}: {
  kind: "receipt" | "issue";
  go: (route: Route) => void;
}) {
  const app = useApp(),
    data = app.snapshot!,
    rows = effectiveInventory(data);
  const [lines, setLines] = useState<DraftLine[]>([blank()]),
    [reason, setReason] = useState(
      kind === "receipt" ? "Recepción de mercancía" : "",
    ),
    [supplier, setSupplier] = useState(0),
    [reference, setReference] = useState(""),
    [saving, setSaving] = useState(false);
  const locked = useRef(false),
    operationKey = useRef(newKey());
  const receipt = kind === "receipt";
  function update(id: string, values: Partial<DraftLine>) {
    setLines((current) =>
      current.map((l) => (l.id === id ? { ...l, ...values } : l)),
    );
  }
  async function save() {
    if (locked.current) return;
    locked.current = true;
    setSaving(true);
    try {
      if (!reason.trim()) throw new Error("Captura el motivo de la operación.");
      const normalized: ReceiptLine[] = lines.map((line, index) => {
        if (!line.ingredient)
          throw new Error(
            `Selecciona el ingrediente del renglón ${index + 1}.`,
          );
        const result: ReceiptLine = {
          ingredient_id: line.ingredient,
          quantity: decimalInput(line.quantity),
        };
        if (receipt) {
          result.unit_cost = line.cost.trim()
            ? decimalInput(line.cost, 6, false)
            : null;
          result.code = line.code.trim();
          if (line.expiry.trim()) {
            const value = line.expiry.trim(),
              parsed = new Date(value + "T12:00:00Z");
            if (
              !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
              Number.isNaN(parsed.getTime()) ||
              parsed.toISOString().slice(0, 10) !== value
            )
              throw new Error(
                `La caducidad del renglón ${index + 1} debe ser una fecha válida AAAA-MM-DD.`,
              );
            result.expires_on = value;
          }
          if (line.presentation) result.presentation_id = line.presentation;
        }
        return result;
      });
      const command: InventoryCommand = {
        key: operationKey.current,
        kind,
        reason: reason.trim(),
        lines: normalized,
      };
      if (receipt) {
        if (supplier) command.supplier_id = supplier;
        if (reference.trim()) command.reference = reference.trim();
      }
      await app.enqueue(
        command,
        `${normalized.length} ${normalized.length === 1 ? "ingrediente" : "renglones"} · ${reason.trim()}`,
      );
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert(
        "Captura guardada",
        "La operación está protegida en este teléfono. Consulta si ya se confirmó o sigue pendiente de conexión.",
        [{ text: "Ver estado", onPress: () => go("sync") }],
      );
      go("sync");
    } catch (error) {
      Alert.alert(
        "Revisa la captura",
        error instanceof Error
          ? error.message
          : "No se pudo guardar. Conservamos el formulario.",
      );
    } finally {
      locked.current = false;
      setSaving(false);
    }
  }
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={{ flex: 1 }}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={s.content}
      >
        <Button
          title="Volver al inicio"
          secondary
          icon="arrow-back"
          onPress={() => go("home")}
        />
        <Title
          sub={
            receipt
              ? "Una recepción, varios ingredientes y lotes trazables."
              : "Consumo de inventario por primeras entradas, primeras salidas."
          }
        >
          {receipt ? "Registrar entrada." : "Registrar salida."}
        </Title>
        <Card>
          <Text style={s.h2}>01 · Datos de la operación</Text>
          {receipt && (
            <>
              <Select
                label="Proveedor · opcional"
                value={supplier}
                options={[
                  { id: 0, label: "Sin proveedor" },
                  ...data.suppliers.map((s) => ({ id: s.id, label: s.name })),
                ]}
                onChange={setSupplier}
              />
              <Field
                label="Referencia de compra · opcional"
                value={reference}
                onChangeText={setReference}
                maxLength={100}
                placeholder="Factura o nota de compra"
              />
            </>
          )}
          <Field
            label={
              receipt ? "Observaciones de recepción" : "Motivo de la salida"
            }
            value={reason}
            onChangeText={setReason}
            maxLength={300}
            multiline
            placeholder={
              receipt
                ? "Detalle de la mercancía recibida"
                : "Ej. Preparación del servicio de cocina"
            }
          />
        </Card>
        <Text style={s.h2}>
          02 · {receipt ? "Ingredientes recibidos" : "Ingredientes a consumir"}
        </Text>
        {lines.map((line, index) => {
          const item = rows.find((i) => i.id === line.ingredient),
            presentations = data.presentations.filter(
              (p) => p.ingredient_id === line.ingredient,
            );
          return (
            <Card key={line.id}>
              <View style={s.between}>
                <Text style={s.h2}>Renglón {index + 1}</Text>
                {lines.length > 1 && (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Quitar renglón ${index + 1}`}
                    onPress={() =>
                      setLines((current) =>
                        current.filter((l) => l.id !== line.id),
                      )
                    }
                    hitSlop={12}
                  >
                    <Icon name="trash-outline" color={C.clay} size={20} />
                  </Pressable>
                )}
              </View>
              <Select
                label="Ingrediente"
                value={line.ingredient}
                options={rows.map((i) => ({
                  id: i.id,
                  label: i.name,
                  detail: `${quantity(i.available)} ${i.unit} disponibles en la descarga`,
                }))}
                onChange={(id) =>
                  update(line.id, { ingredient: id, presentation: 0 })
                }
              />
              {item && (
                <Text style={s.tiny}>
                  Unidad base: {item.unit} · Disponible descargado:{" "}
                  {quantity(item.available)} {item.unit}
                </Text>
              )}
              {receipt && item && presentations.length > 0 && (
                <Select
                  label="Presentación de compra"
                  value={line.presentation}
                  options={[
                    { id: 0, label: `Capturar en ${item.unit}` },
                    ...presentations.map((p) => ({
                      id: p.id,
                      label: p.name,
                      detail: `${quantity(p.base_quantity)} ${item.unit} por presentación`,
                    })),
                  ]}
                  onChange={(id) => update(line.id, { presentation: id })}
                />
              )}
              <Field
                label={
                  line.presentation
                    ? "Cantidad de presentaciones"
                    : `Cantidad${item ? " · " + item.unit : " en unidad base"}`
                }
                keyboardType="decimal-pad"
                value={line.quantity}
                onChangeText={(quantity) => update(line.id, { quantity })}
                placeholder="0.000000"
              />
              {receipt && (
                <>
                  <Field
                    label={
                      line.presentation
                        ? "Costo por presentación · MXN · opcional"
                        : "Costo por unidad base · MXN · opcional"
                    }
                    keyboardType="decimal-pad"
                    value={line.cost}
                    onChangeText={(cost) => update(line.id, { cost })}
                    placeholder="Vacío si aún es desconocido"
                  />
                  <Field
                    label="Código de lote · opcional"
                    value={line.code}
                    onChangeText={(code) => update(line.id, { code })}
                    maxLength={100}
                  />
                  <Field
                    label="Caducidad · AAAA-MM-DD · opcional"
                    value={line.expiry}
                    onChangeText={(expiry) => update(line.id, { expiry })}
                    maxLength={10}
                    placeholder="2026-12-31"
                    keyboardType="numbers-and-punctuation"
                  />
                </>
              )}
            </Card>
          );
        })}
        <Button
          title="Agregar ingrediente"
          secondary
          icon="add-outline"
          onPress={() => setLines((current) => [...current, blank()])}
          disabled={lines.length >= 100}
        />
        <Note warning>
          {receipt
            ? "La entrada se registra en Render al sincronizar; ese momento determina su orden PEPS. La fecha de captura local se conserva en el teléfono. Un costo vacío permanece desconocido."
            : "La disponibilidad descargada puede cambiar por ventas de la web u otros teléfonos. Render validará todos los renglones y asignará los lotes PEPS sin permitir sobreconsumo."}
        </Note>
        {!rows.length && (
          <Note warning>
            No hay ingredientes descargados. Crea los catálogos en la web y
            sincroniza antes de registrar movimientos.
          </Note>
        )}
        <Button
          title={
            receipt
              ? "Guardar entrada para sincronizar"
              : "Guardar salida para sincronizar"
          }
          onPress={save}
          loading={saving}
          disabled={!rows.length}
          icon="cloud-upload-outline"
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
