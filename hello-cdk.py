from aws_cdk import core
from aws_cdk.aws_ec2 import (
    Vpc,
    SubnetType,
    SecurityGroup,
    Peer,
    Port
)
from aws_cdk.aws_rds import DatabaseInstance, DatabaseInstanceEngine, SubnetGroup
from aws_cdk.aws_ec2 import InstanceType, AmazonLinuxImage
from aws_cdk.aws_s3 import Bucket, BlockPublicAccess, BucketAccessControl
from aws_cdk.aws_s3_deployment import Source, BucketDeployment

class NetworkStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC
        vpc = Vpc(self, "MyVpc", max_azs=2)

        # Create public subnet in first availability zone
        public_subnet_1 = vpc.add_subnet(subnet_type=SubnetType.PUBLIC, availability_zone='us-east-1a', cidr_mask=24)

        # Create private subnet in first availability zone
        private_subnet_1 = vpc.add_subnet(subnet_type=SubnetType.PRIVATE, availability_zone='us-east-1a', cidr_mask=24)

        # Create public subnet in second availability zone
        public_subnet_2 = vpc.add_subnet(subnet_type=SubnetType.PUBLIC, availability_zone='us-east-1b', cidr_mask=24)

        # Create private subnet in second availability zone
        private_subnet_2 = vpc.add_subnet(subnet_type=SubnetType.PRIVATE, availability_zone='us-east-1b', cidr_mask=24)

        # Output the subnet IDs for reference
        core.CfnOutput(self, "PublicSubnet1", value=public_subnet_1.subnet_id)
        core.CfnOutput(self, "PrivateSubnet1", value=private_subnet_1.subnet_id)
        core.CfnOutput(self, "PublicSubnet2", value=public_subnet_2.subnet_id)
        core.CfnOutput(self, "PrivateSubnet2", value=private_subnet_2.subnet_id)


class ServerStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Security group for web servers
        web_server_sg = SecurityGroup(self, "WebServerSG", vpc=vpc)
        web_server_sg.add_ingress_rule(Peer.any_ipv4(), Port.tcp(80), "Allow inbound HTTP traffic")

        # Security group for RDS instance
        rds_sg = SecurityGroup(self, "RDSSG", vpc=vpc)
        rds_sg.add_ingress_rule(web_server_sg, Port.tcp(3306), "Allow inbound MySQL traffic from web servers")

        # Create RDS subnet group
        rds_subnet_group = SubnetGroup(self, "RDSSubnetGroup", vpc_subnets={'subnet_type': SubnetType.PRIVATE})

        # Create RDS instance
        rds_instance = DatabaseInstance(self, "MyRDSInstance",
                                        engine=DatabaseInstanceEngine.mysql(version='8.0'),
                                        vpc=vpc,
                                        subnet_group=rds_subnet_group,
                                        security_groups=[rds_sg],
                                        removal_policy=core.RemovalPolicy.DESTROY,
                                        instance_type=InstanceType.of(InstanceType.BURSTABLE2, 'micro'))

        # Create S3 bucket
        bucket = Bucket(self, "MyFirstBucket",
                        block_public_access=BlockPublicAccess.BLOCK_ACLS,
                        access_control=BucketAccessControl.BUCKET_OWNER_FULL_CONTROL,
                        public_read_access=True,
                        website_index_document="index.html",
                        versioned=True,
                        removal_policy=core.RemovalPolicy.DESTROY,
                        auto_delete_objects=True)

        # Deploy static website to S3 bucket
        deployment = BucketDeployment(self, "DeployWebsite",
                                      sources=[Source.asset('./hello_cdk/static-website.zip')],
                                      destination_bucket=bucket)

app = core.App()

# Create network stack
network_stack = NetworkStack(app, "NetworkStack")

# Create server stack with reference to the VPC created in the network stack
server_stack = ServerStack(app, "ServerStack", vpc=network_stack.vpc)

app.synth()
