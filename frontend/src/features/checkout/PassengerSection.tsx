import type { UseFormReturn } from "react-hook-form";
import type { Fare } from "@/api/client";
import { DocumentIcon } from "@/components/icons";
import { formatDate } from "@/lib/format";
import { FieldError, FormField, FormSection, inputClass, selectClass } from "./fields";
import {
  ADULT_AGE,
  airlineNameLength,
  type CheckoutValues,
  countries,
  isTransliterated,
  MAX_NAME_LENGTH,
  TITLES,
  toAirlineName,
} from "./logic";

// Built once: the list of every country, named in Spanish.
const COUNTRIES = countries();

/** "Pasajero 1 · Adulto" (design board "Pasajeros y pago"). */
export function PassengerSection({
  form,
  fare,
  departureDate,
}: {
  form: UseFormReturn<CheckoutValues>;
  fare: Fare;
  departureDate: string;
}) {
  const {
    register,
    watch,
    formState: { errors },
  } = form;
  const [givenName, familyName] = watch(["givenName", "familyName"]);
  const nameLength = airlineNameLength(givenName, familyName);
  const transliterated = [givenName, familyName].some(isTransliterated);
  const err = (name: keyof CheckoutValues) => errors[name]?.message;
  const described = (name: keyof CheckoutValues) => (err(name) ? `${name}-error` : undefined);

  return (
    <FormSection
      id="passenger-1"
      title="Pasajero 1 · Adulto"
      aside="Escribí los datos tal como figuran en el documento de viaje"
    >
      <div className="grid grid-cols-1 gap-x-3 gap-y-3.5 p-[18px] sm:grid-cols-6">
        <FormField className="sm:col-span-1" id="title" label="Tratamiento">
          <select
            id="title"
            {...register("title")}
            aria-invalid={!!err("title")}
            aria-describedby={described("title")}
            className={selectClass(!!err("title"))}
          >
            <option value="">Elegir</option>
            {TITLES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <FieldError id="title-error" message={err("title")} />
        </FormField>
        <FormField className="sm:col-span-2" id="givenName" label="Nombre">
          <input
            id="givenName"
            {...register("givenName", { deps: ["familyName"] })}
            autoComplete="given-name"
            aria-invalid={!!err("givenName")}
            aria-describedby={described("givenName")}
            className={inputClass(!!err("givenName"))}
          />
          <FieldError id="givenName-error" message={err("givenName")} />
        </FormField>
        <FormField className="sm:col-span-3" id="familyName" label="Apellido">
          <input
            id="familyName"
            {...register("familyName")}
            autoComplete="family-name"
            aria-invalid={!!err("familyName")}
            aria-describedby={described("familyName")}
            className={inputClass(!!err("familyName"))}
          />
          <FieldError id="familyName-error" message={err("familyName")} />
        </FormField>
        <p className="-mt-1 flex justify-between gap-3 text-[12px] text-muted sm:col-span-6">
          <span>
            Nombre y apellido juntos no pueden superar los {MAX_NAME_LENGTH} caracteres. Las tildes y la ñ se
            transliteran (Muñoz → MUNOZ) con aviso previo.
          </span>
          <span
            className={
              nameLength > MAX_NAME_LENGTH
                ? "font-mono whitespace-nowrap text-bad"
                : "font-mono whitespace-nowrap"
            }
          >
            {nameLength} / {MAX_NAME_LENGTH}
          </span>
        </p>
        {transliterated && (
          <p
            role="status"
            className="rounded-md bg-warn-soft px-3 py-2 text-[13px] text-warn-ink sm:col-span-6"
          >
            A la aerolínea se envía como{" "}
            <strong className="font-mono">
              {toAirlineName(givenName) ?? givenName} {toAirlineName(familyName) ?? familyName}
            </strong>
            , sin tildes ni ñ, como lo leen sus sistemas.
          </p>
        )}

        <fieldset
          className="flex min-w-0 flex-col gap-1.5 sm:col-span-2"
          aria-describedby={described("gender")}
        >
          <legend className="mb-1.5 text-[13px] font-semibold">Género (según el documento)</legend>
          <div
            className={
              err("gender")
                ? "inline-flex overflow-hidden rounded-md border-2 border-bad-strong text-[14px]"
                : "inline-flex overflow-hidden rounded-md border border-subtle text-[14px]"
            }
          >
            <label className="flex h-[42px] flex-1 items-center gap-2 px-3">
              <input type="radio" value="m" {...register("gender")} />
              Masculino
            </label>
            <label className="flex h-[42px] flex-1 items-center gap-2 border-l border-subtle px-3">
              <input type="radio" value="f" {...register("gender")} />
              Femenino
            </label>
          </div>
          <FieldError id="gender-error" message={err("gender")} />
        </fieldset>
        <fieldset
          className="flex min-w-0 flex-col gap-1.5 sm:col-span-2"
          aria-describedby={described("birthDay")}
        >
          <legend className="mb-1.5 text-[13px] font-semibold">Fecha de nacimiento</legend>
          <div className="grid grid-cols-[1fr_1fr_1.4fr] gap-1.5">
            <input
              {...register("birthDay")}
              aria-label="Día"
              placeholder="DD"
              inputMode="numeric"
              maxLength={2}
              aria-invalid={!!err("birthDay")}
              className={inputClass(!!err("birthDay"), true)}
            />
            <input
              {...register("birthMonth", { deps: ["birthDay"] })}
              aria-label="Mes"
              placeholder="MM"
              inputMode="numeric"
              maxLength={2}
              aria-invalid={!!err("birthDay")}
              className={inputClass(!!err("birthDay"), true)}
            />
            <input
              {...register("birthYear", { deps: ["birthDay"] })}
              aria-label="Año"
              placeholder="AAAA"
              inputMode="numeric"
              maxLength={4}
              aria-invalid={!!err("birthDay")}
              className={inputClass(!!err("birthDay"), true)}
            />
          </div>
          <FieldError id="birthDay-error" message={err("birthDay")} />
        </fieldset>
        <p className="text-[12px] leading-[1.45] text-muted sm:col-span-2 sm:mt-[22px]">
          Un adulto debe tener {ADULT_AGE} años o más el {formatDate(departureDate)}.
        </p>

        <FormField className="sm:col-span-3" id="email" label="Email">
          <input
            id="email"
            {...register("email")}
            type="email"
            autoComplete="email"
            aria-invalid={!!err("email")}
            aria-describedby={described("email")}
            className={inputClass(!!err("email"))}
          />
          <FieldError id="email-error" message={err("email")} />
        </FormField>
        <div className="flex min-w-0 flex-col gap-1.5 sm:col-span-3">
          <span id="phone-label" className="text-[13px] font-semibold">
            Teléfono
          </span>
          <div className="grid grid-cols-[110px_minmax(0,1fr)] gap-1.5">
            <select
              {...register("phoneCountry", { deps: ["phoneNumber"] })}
              aria-label="Código de país"
              className={selectClass(false, true)}
            >
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code} title={c.name}>
                  {c.code} +{c.callingCode}
                </option>
              ))}
            </select>
            <input
              {...register("phoneNumber")}
              aria-labelledby="phone-label"
              type="tel"
              autoComplete="tel-national"
              placeholder="9 11 …"
              aria-invalid={!!err("phoneNumber")}
              aria-describedby={described("phoneNumber") ?? "phone-hint"}
              className={inputClass(!!err("phoneNumber"), true)}
            />
          </div>
          {err("phoneNumber") ? (
            <FieldError id="phoneNumber-error" message={err("phoneNumber")} />
          ) : (
            <span id="phone-hint" className="text-[12px] text-muted">
              Se envía en formato internacional: +54911…
            </span>
          )}
        </div>
      </div>

      {fare.requires_identity_documents ? (
        <fieldset className="mx-[18px] mb-[18px] grid grid-cols-1 gap-3 rounded-md border border-line p-3.5 sm:grid-cols-6">
          <legend className="px-1 text-[13px] font-semibold">Pasaporte (lo pide esta tarifa)</legend>
          <FormField className="sm:col-span-2" id="passportNumber" label="Número">
            <input
              id="passportNumber"
              {...register("passportNumber")}
              aria-invalid={!!err("passportNumber")}
              aria-describedby={described("passportNumber")}
              className={inputClass(!!err("passportNumber"), true)}
            />
            <FieldError id="passportNumber-error" message={err("passportNumber")} />
          </FormField>
          <FormField className="sm:col-span-2" id="passportCountry" label="País emisor">
            <select id="passportCountry" {...register("passportCountry")} className={selectClass(false)}>
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name}
                </option>
              ))}
            </select>
          </FormField>
          <FormField className="sm:col-span-2" id="passportExpiry" label="Vencimiento">
            <input
              id="passportExpiry"
              {...register("passportExpiry")}
              placeholder="DD/MM/AAAA"
              inputMode="numeric"
              aria-invalid={!!err("passportExpiry")}
              aria-describedby={described("passportExpiry")}
              className={inputClass(!!err("passportExpiry"), true)}
            />
            <FieldError id="passportExpiry-error" message={err("passportExpiry")} />
          </FormField>
        </fieldset>
      ) : (
        <div className="mx-[18px] mb-[18px] flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border border-dashed border-subtle px-3.5 py-3 text-[13px] text-ink-2">
          <DocumentIcon className="text-muted" />
          <span className="flex-1">Esta oferta no pide pasaporte.</span>
        </div>
      )}
    </FormSection>
  );
}
