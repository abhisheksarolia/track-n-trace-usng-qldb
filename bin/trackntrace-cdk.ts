#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { TrackntraceCdkStack } from '../lib/trackntrace-cdk-stack';

const app = new cdk.App();
new TrackntraceCdkStack(app, 'TrackntraceCdkStack');
