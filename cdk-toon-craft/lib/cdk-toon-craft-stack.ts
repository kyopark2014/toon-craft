import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from 'aws-cdk-lib/aws-iam';
import * as path from "path";

// import * as sqs from 'aws-cdk-lib/aws-sqs';
const region = process.env.CDK_DEFAULT_REGION;    
const accountId = process.env.CDK_DEFAULT_ACCOUNT;
const projectName = `toon-craft`; 

export class CdkToonCraftStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // lambda-tool
    const roleLambdaTools = new iam.Role(this, `role-lambda-tools-for-${projectName}`, {
      roleName: `role-lambda-tools-for-${projectName}-${region}`,
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal("lambda.amazonaws.com"),
        new iam.ServicePrincipal("bedrock.amazonaws.com"),
      ),
      // managedPolicies: [cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')] 
    });
    // roleLambdaTools.addManagedPolicy({  // grant log permission
    //   managedPolicyArn: 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
    // });
    const CreateLogPolicy = new iam.PolicyStatement({  
      resources: [`arn:aws:logs:${region}:${accountId}:*`],
      actions: ['logs:CreateLogGroup'],
    });        
    roleLambdaTools.attachInlinePolicy( 
      new iam.Policy(this, `create-log-policy-lambda-tools-for-${projectName}`, {
        statements: [CreateLogPolicy],
      }),
    );
    const CreateLogStreamPolicy = new iam.PolicyStatement({  
      resources: [`arn:aws:logs:${region}:${accountId}:log-group:/aws/lambda/*`],
      actions: ["logs:CreateLogStream","logs:PutLogEvents"],
    });        
    roleLambdaTools.attachInlinePolicy( 
      new iam.Policy(this, `create-stream-log-policy-lambda-tools-for-${projectName}`, {
        statements: [CreateLogStreamPolicy],
      }),
    ); 

    const lambdaName = `toons-craft-upload`;
    const lambdaUpload = new lambda.DockerImageFunction(this, `lambda-tools-for-${projectName}`, {
      description: 'toons-craft upload api',
      functionName: lambdaName,
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../lambda-upload')),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {
      }
    });
    
    const lambdaSelect = new lambda.DockerImageFunction(this, `lambda-select-for-${projectName}`, {
      description: 'selection api of toon-craft',
      functionName: 'toons-craft-select',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../lambda-select')),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {
      }
    });

    const lambdaRecommend = new lambda.DockerImageFunction(this, `lambda-recommend-for-${projectName}`, {
      description: 'recommend api of toon-craft',
      functionName: 'toons-craft-recommend',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../lambda-recommend')),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {
      }
    });

    const lambdaRetrieve = new lambda.DockerImageFunction(this, `lambda-retrieve-for-${projectName}`, {
      description: 'retrieve api of toon-craft',
      functionName: 'toons-craft-retrieve',
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../lambda-retrieve')),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {
      }
    });

    const lambdaHistory = new lambda.DockerImageFunction(this, `lambda-history-for-${projectName}`, {
      description: "history api of toon-craft",
      functionName: "toons-craft-history",
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "../../lambda-history")
      ),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {

      },
    });

    const lambdaLatest = new lambda.DockerImageFunction(this, `lambda-latest-for-${projectName}`, {
      description: "latest api of toon-craft",
      functionName: "toons-craft-latest",
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, "../../lambda-latest")
      ),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {

      },
    });

    const lambdaGenImage = new lambda.DockerImageFunction(this, `lambda-gen-image-for-${projectName}`, {
      description: 'toons-craft gen-image api',
      functionName: `toons-craft-gen-image`,
      code: lambda.DockerImageCode.fromImageAsset(path.join(__dirname, '../../lambda-gen-image')),
      timeout: cdk.Duration.seconds(180),
      role: roleLambdaTools,
      environment: {
      }
    });
  }
}
