import type { UseFormReturn } from "react-hook-form";
import type { Fare } from "@/api/client";
import { formatTotal, formatUtcDateTime } from "@/lib/format";
import { FieldError, FormField, FormSection, inputClass } from "./fields";
import type { CheckoutValues } from "./logic";

/** "Cuándo pagar" and the card (design board "Pasajeros y pago"). */
export function PaymentSection({
  form,
  fare,
  airline,
}: {
  form: UseFormReturn<CheckoutValues>;
  fare: Fare;
  airline: string;
}) {
  const {
    register,
    formState: { errors },
  } = form;
  const err = (name: keyof CheckoutValues) => errors[name]?.message;
  const described = (name: keyof CheckoutValues) => (err(name) ? `${name}-error` : undefined);
  const holdUntil = fare.payment.payment_required_by;

  return (
    <FormSection id="pay" title="Cuándo pagar">
      <div
        role="radiogroup"
        aria-labelledby="pay"
        className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-3 p-[18px]"
      >
        <label className="flex items-start gap-3 rounded-lg border-2 border-action bg-action-tint p-3.5">
          <input
            type="radio"
            name="payWhen"
            checked
            readOnly
            className="mt-[3px] h-[18px] w-[18px] accent-action"
          />
          <span className="flex flex-col gap-1 text-[14px]">
            <strong>Pagar ahora</strong>
            <span className="text-ink-2">
              Se emite el ticket al confirmar.{" "}
              <span className="font-mono font-semibold text-ink">{formatTotal(fare.price.total)}</span>
            </span>
          </span>
        </label>
        {/* For now every booking is paid at once: holding it comes later. */}
        <label className="flex items-start gap-3 rounded-lg border border-dashed border-line-dash bg-surface-2 p-3.5 text-muted-2">
          <input type="radio" name="payWhen" disabled className="mt-[3px] h-[18px] w-[18px]" />
          <span className="flex flex-col gap-1 text-[14px]">
            <strong>Reservar ahora y pagar después · próximamente</strong>
            <span>
              {fare.payment.can_hold && holdUntil ? (
                <>
                  El lugar quedaría guardado hasta el{" "}
                  <span className="font-mono">{formatUtcDateTime(holdUntil)}</span>. {airline} no garantiza el
                  precio hasta que pagues.
                </>
              ) : (
                "Esta tarifa se paga al reservar."
              )}
            </span>
          </span>
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3 px-[18px] pb-[18px] sm:grid-cols-4">
        <FormField className="col-span-2 sm:col-span-4" id="cardNumber" label="Número de tarjeta">
          <input
            id="cardNumber"
            {...register("cardNumber")}
            autoComplete="cc-number"
            inputMode="numeric"
            aria-invalid={!!err("cardNumber")}
            aria-describedby={described("cardNumber")}
            className={inputClass(!!err("cardNumber"), true)}
          />
          <FieldError id="cardNumber-error" message={err("cardNumber")} />
        </FormField>
        <FormField className="col-span-2" id="cardHolder" label="Titular">
          <input
            id="cardHolder"
            {...register("cardHolder")}
            autoComplete="cc-name"
            aria-invalid={!!err("cardHolder")}
            aria-describedby={described("cardHolder")}
            className={inputClass(!!err("cardHolder"))}
          />
          <FieldError id="cardHolder-error" message={err("cardHolder")} />
        </FormField>
        <FormField id="cardExpiry" label="Vencimiento">
          <input
            id="cardExpiry"
            {...register("cardExpiry")}
            autoComplete="cc-exp"
            placeholder="MM/AA"
            aria-invalid={!!err("cardExpiry")}
            aria-describedby={described("cardExpiry")}
            className={inputClass(!!err("cardExpiry"), true)}
          />
          <FieldError id="cardExpiry-error" message={err("cardExpiry")} />
        </FormField>
        <FormField id="cardCode" label="Código">
          <input
            id="cardCode"
            {...register("cardCode")}
            autoComplete="cc-csc"
            inputMode="numeric"
            maxLength={4}
            aria-invalid={!!err("cardCode")}
            aria-describedby={described("cardCode")}
            className={inputClass(!!err("cardCode"), true)}
          />
          <FieldError id="cardCode-error" message={err("cardCode")} />
        </FormField>
        <p className="col-span-2 text-[12px] text-muted sm:col-span-4">
          Pago simulado: este entorno de prueba no cobra ninguna tarjeta real. El número y el código no salen
          de tu navegador.
        </p>
      </div>
    </FormSection>
  );
}
