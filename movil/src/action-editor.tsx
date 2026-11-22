import React, { useRef, useState } from "react";
import { Alert, Modal, ScrollView, Switch, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useApp, newKey } from "./context";
import { toolFields, toolLabels, type Plan } from "./assistant-actions";
import { decimalInput } from "./domain";
import { Button, Card, Chip, Field, Label, Note, s } from "./ui";
import type { CatalogCommand } from "./types";

export function ActionEditor({
  plan,
  onClose,
}: {
  plan: Plan;
  onClose: () => void;
}) {
  const app = useApp(),
    fields = toolFields(plan.kind, app.snapshot!),
    [data, setData] = useState<CatalogCommand["data"]>(plan.data),
    [preview, setPreview] = useState<CatalogCommand["data"] | null>(null),
    [saving, setSaving] = useState(false),
    lock = useRef(false),
    actionKey = useRef(newKey());
  function review() {
    try {
      const result: CatalogCommand["data"] = {};
      for (const field of fields) {
        const value = data[field.key];
        if (field.type === "boolean") {
          result[field.key] = value === undefined ? true : value === true;
          continue;
        }
        if (field.type === "choice") {
          const id = Number(value || 0);
          if (field.required && !id)
            throw new Error("Selecciona " + field.label.toLowerCase() + ".");
          if (id && !field.options?.some((o) => o.id === id))
            throw new Error(
              "Sincroniza y revisa " + field.label.toLowerCase() + ".",
            );
          result[field.key] = id;
          continue;
        }
        const text = String(value ?? "").trim();
        if (field.required && !text)
          throw new Error("Completa " + field.label.toLowerCase() + ".");
        result[field.key] = text
          ? field.type === "decimal"
            ? decimalInput(text, 6, field.key === "base_quantity")
            : text
          : null;
      }
      setPreview(result);
    } catch (e) {
      Alert.alert(
        "Revisa los datos",
        e instanceof Error ? e.message : "Completa los campos.",
      );
    }
  }
  async function execute() {
    if (lock.current || !preview) return;
    lock.current = true;
    setSaving(true);
    try {
      await app.enqueue(
        { key: actionKey.current, kind: plan.kind, data: preview },
        toolLabels[plan.kind] + " · " + String(preview.name),
      );
      onClose();
      Alert.alert(
        "Acción guardada",
        "Consulta en Conexión si ya tiene confirmación de Render o sigue pendiente. No vuelvas a crearla si todavía se está sincronizando.",
      );
    } catch (e) {
      Alert.alert(
        "No se pudo guardar",
        e instanceof Error ? e.message : "Intenta nuevamente.",
      );
    } finally {
      lock.current = false;
      setSaving(false);
    }
  }
  return (
    <Modal visible animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={s.screen}>
        <ScrollView
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={s.content}
        >
          <Text style={s.eyebrow}>C7 · ACCIÓN GUIADA</Text>
          <Text style={s.title}>{toolLabels[plan.kind]}</Text>
          <Note>
            Se aplican los mismos permisos y validaciones de la web. Crear un
            ingrediente no crea existencias: las entradas se registran por
            separado.
          </Note>
          {preview ? (
            <>
              <Card>
                <Text style={s.h2}>Revisa antes de guardar</Text>
                {fields.map((field) => (
                  <View key={field.key}>
                    <Label>{field.label}</Label>
                    <Text style={s.body}>
                      {field.type === "choice"
                        ? field.options?.find(
                            (o) => o.id === preview[field.key],
                          )?.name || "Sin selección"
                        : typeof preview[field.key] === "boolean"
                          ? preview[field.key]
                            ? "Sí"
                            : "No"
                          : String(preview[field.key] ?? "Sin registrar")}
                    </Text>
                  </View>
                ))}
              </Card>
              <Button
                title="Corregir datos"
                secondary
                onPress={() => setPreview(null)}
              />
              <Button
                title="Confirmar y guardar acción"
                loading={saving}
                onPress={execute}
              />
            </>
          ) : (
            fields.map((field) => (
              <View key={field.key} style={{ gap: 10 }}>
                {field.type === "boolean" ? (
                  <View style={s.between}>
                    <Label>{field.label}</Label>
                    <Switch
                      accessibilityLabel={field.label}
                      value={
                        data[field.key] === undefined
                          ? true
                          : data[field.key] === true
                      }
                      onValueChange={(value) =>
                        setData((d) => ({ ...d, [field.key]: value }))
                      }
                    />
                  </View>
                ) : field.type === "choice" ? (
                  <>
                    <Label>{field.label}</Label>
                    <View
                      style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}
                    >
                      {field.options?.map((option) => (
                        <Chip
                          key={option.id}
                          label={option.name}
                          active={Number(data[field.key] || 0) === option.id}
                          onPress={() =>
                            setData((d) => ({ ...d, [field.key]: option.id }))
                          }
                        />
                      ))}
                    </View>
                    {!field.options?.length && (
                      <Note warning>
                        No hay opciones descargadas. Sincroniza o crea primero
                        este catálogo en Sistema.
                      </Note>
                    )}
                  </>
                ) : (
                  <Field
                    label={field.label}
                    value={String(data[field.key] ?? "")}
                    keyboardType={
                      field.type === "decimal" ? "decimal-pad" : "default"
                    }
                    onChangeText={(value) =>
                      setData((d) => ({ ...d, [field.key]: value }))
                    }
                  />
                )}
              </View>
            ))
          )}
          {!preview && <Button title="Revisar acción" onPress={review} />}
          <Button title="Cerrar sin guardar" secondary onPress={onClose} />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}
