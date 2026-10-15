import React from "react";import {createRoot} from "react-dom/client";import "./base.css";
import Hero from "./src/components/Hero";
import Workspace from "./src/components/Workspace";
import Principles from "./src/components/Principles";
import Plans from "./src/components/Plans";
import Footer from "./src/components/Footer";
createRoot(document.getElementById("root")!).render(<><a className="skip" href="#main">Skip to content</a><main id="main"><Hero/><Workspace/><Principles/><Plans/><Footer/></main></>);