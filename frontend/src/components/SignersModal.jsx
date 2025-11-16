import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

const SignersModal = ({ open, onOpenChange, onConfirm }) => {
  const [signers, setSigners] = useState([{ nombre: "", correo: "", telefono: "" }]);

  const handleSignerChange = (index, field, value) => {
    const newSigners = [...signers];
    newSigners[index][field] = value;
    setSigners(newSigners);
  };

  const addSigner = () => {
    setSigners([...signers, { nombre: "", correo: "", telefono: "" }]);
  };

  const handleConfirm = () => {
    // Aquí se podría agregar validación antes de confirmar
    onConfirm(signers);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Información de los Firmantes</DialogTitle>
          <DialogDescription>
            Por favor, ingresa los datos de las personas que firmarán el contrato.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {signers.map((signer, index) => (
            <div key={index} className="space-y-2 p-4 border rounded-md">
              <h4 className="font-semibold">Firmante {index + 1}</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor={`nombre-${index}`}>Nombre completo</Label>
                  <Input
                    id={`nombre-${index}`}
                    value={signer.nombre}
                    onChange={(e) => handleSignerChange(index, "nombre", e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`correo-${index}`}>Correo electrónico</Label>
                  <Input
                    id={`correo-${index}`}
                    type="email"
                    value={signer.correo}
                    onChange={(e) => handleSignerChange(index, "correo", e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`telefono-${index}`}>Teléfono</Label>
                  <Input
                    id={`telefono-${index}`}
                    value={signer.telefono}
                    onChange={(e) => handleSignerChange(index, "telefono", e.target.value)}
                  />
                </div>
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={addSigner}>
            Agregar otro firmante
          </Button>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleConfirm}>Confirmar y Generar Contrato</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default SignersModal;
