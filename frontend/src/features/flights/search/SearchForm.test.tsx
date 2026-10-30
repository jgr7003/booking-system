import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { renderApp } from "@/test/render";
import { PassengersField, type PassengersValue } from "./PassengersField";

/** The passengers field without the current limit of one adult. */
function UnlimitedPassengers() {
  const [value, setValue] = useState<PassengersValue>({ adults: 1, children: [] });
  return <PassengersField value={value} onChange={setValue} />;
}

describe("search form", () => {
  it("suggests cities and airports and picks one with the keyboard", async () => {
    const user = userEvent.setup();
    renderApp("/");

    const origin = await screen.findByRole("combobox", { name: "Origen" });
    await user.type(origin, "new y");

    const list = await screen.findByRole("listbox", { name: "Sugerencias para origen" });
    // Suggestions arrive after the 200 ms debounce and the request.
    expect(
      await within(list).findByRole("option", { name: /New York · todos los aeropuertos/ }),
    ).toBeInTheDocument();

    await user.keyboard("{Enter}");

    expect(origin).toHaveValue("New York · todos los aeropuertos");
    expect(screen.getByText("NYC")).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("books one adult for now", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: /Pasajeros/ }));

    expect(screen.getByRole("button", { name: "Agregar adulto" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Agregar menor/ })).toBeDisabled();
    expect(screen.getByText(/Más pasajeros, próximamente/)).toBeInTheDocument();
  });

  it("each infant needs a different adult (when more passengers are allowed)", async () => {
    const user = userEvent.setup();
    render(<UnlimitedPassengers />);

    await user.click(screen.getByRole("button", { name: /Pasajeros/ }));
    await user.click(screen.getByRole("button", { name: /Agregar menor/ }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Menor 1" }), "0");
    await user.click(screen.getByRole("button", { name: /Agregar menor/ }));

    const second = screen.getByRole("combobox", { name: "Menor 2" });
    expect(within(second).getByRole("option", { name: "Menos de 1 año" })).toBeDisabled();
    expect(within(second).getByRole("option", { name: "5 años" })).toBeEnabled();
    expect(screen.getByText(/en brazos de un adulto distinto/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Agregar adulto" }));
    expect(within(second).getByRole("option", { name: "Menos de 1 año" })).toBeEnabled();
  });

  it("validates before searching", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: "Buscar" }));

    expect(screen.getByText("Elige el origen.")).toBeInTheDocument();
    expect(screen.getByText("Elige el destino.")).toBeInTheDocument();
    expect(screen.getByText("Elige la fecha de ida.")).toBeInTheDocument();
  });
});
