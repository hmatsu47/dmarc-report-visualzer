#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { DmarcReportVisualizerStack } from "../lib/dmarc-report-visualizer-stack";

const app = new cdk.App();

const receiveDomain = app.node.tryGetContext("receiveDomain");
if (!receiveDomain) {
  throw new Error("Context variable 'receiveDomain' is required. Use -c receiveDomain=<domain>");
}

new DmarcReportVisualizerStack(app, "DmarcReportVisualizerStack", {
  receiveDomain,
  glacierTransitionDays: Number(app.node.tryGetContext("glacierTransitionDays")) || undefined,
  expirationDays: Number(app.node.tryGetContext("expirationDays")) || undefined,
});
