import boto3
import sys
import time

def cleanup_vpc(vpc_id, region):
    """
    Deletes a VPC and all its dependent resources.
    """
    ec2 = boto3.client('ec2', region_name=region)
    elbv2 = boto3.client('elbv2', region_name=region)

    print(f"Starting cleanup for VPC: {vpc_id} in region: {region}")

    # Terminate EC2 instances
    try:
        print("Terminating instances...")
        instance_reservations = ec2.describe_instances(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Reservations']
        instance_ids = [instance['InstanceId'] for reservation in instance_reservations for instance in reservation['Instances']]
        if instance_ids:
            ec2.terminate_instances(InstanceIds=instance_ids)
            print(f"Waiting for instances to terminate: {instance_ids}")
            waiter = ec2.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=instance_ids)
        print("Instances terminated.")
    except Exception as e:
        print(f"Error terminating instances: {e}")

    # Delete Network Interfaces
    try:
        print("Deleting network interfaces...")
        enis = ec2.describe_network_interfaces(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NetworkInterfaces']
        for eni in enis:
            eni_id = eni['NetworkInterfaceId']
            # Detach first if attached
            if 'Attachment' in eni and 'AttachmentId' in eni['Attachment']:
                attachment_id = eni['Attachment']['AttachmentId']
                print(f"Detaching ENI {eni_id} (attachment {attachment_id})")
                ec2.detach_network_interface(AttachmentId=attachment_id)
                time.sleep(15) # Give it time to detach
            print(f"Deleting ENI: {eni_id}")
            ec2.delete_network_interface(NetworkInterfaceId=eni_id)
        print("Network interfaces deleted.")
    except Exception as e:
        print(f"Error deleting network interfaces: {e}")


    # Delete Load Balancers
    try:
        print("Deleting load balancers...")
        lbs = elbv2.describe_load_balancers()['LoadBalancers']
        vpc_lbs = [lb for lb in lbs if lb.get('VpcId') == vpc_id]
        for lb in vpc_lbs:
            lb_arn = lb['LoadBalancerArn']
            print(f"Deleting LB: {lb_arn}")
            elbv2.delete_load_balancer(LoadBalancerArn=lb_arn)
            # No waiter for LB deletion, so we poll
            while True:
                try:
                    elbv2.describe_load_balancers(LoadBalancerArns=[lb_arn])
                    time.sleep(10)
                except elbv2.exceptions.LoadBalancerNotFoundException:
                    print(f"LB {lb_arn} deleted.")
                    break
    except Exception as e:
        print(f"Error deleting load balancers: {e}")


    # Delete NAT Gateways
    try:
        print("Deleting NAT gateways...")
        nat_gateways = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['NatGateways']
        for ngw in nat_gateways:
            ngw_id = ngw['NatGatewayId']
            print(f"Deleting NAT Gateway: {ngw_id}")
            ec2.delete_nat_gateway(NatGatewayId=ngw_id)
            # Wait for deletion
            waiter = ec2.get_waiter('nat_gateway_deleted')
            waiter.wait(NatGatewayIds=[ngw_id])
            print(f"NAT Gateway {ngw_id} deleted.")
    except Exception as e:
        print(f"Error deleting NAT gateways: {e}")


    # Detach and delete Internet Gateways
    try:
        print("Detaching and deleting Internet Gateways...")
        igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])['InternetGateways']
        for igw in igws:
            igw_id = igw['InternetGatewayId']
            print(f"Detaching IGW {igw_id} from VPC {vpc_id}")
            ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
            print(f"Deleting IGW {igw_id}")
            ec2.delete_internet_gateway(InternetGatewayId=igw_id)
        print("Internet Gateways deleted.")
    except Exception as e:
        print(f"Error deleting Internet Gateways: {e}")
        
    # Delete Subnets
    try:
        print("Deleting subnets...")
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
        for subnet in subnets:
            subnet_id = subnet['SubnetId']
            print(f"Deleting Subnet: {subnet_id}")
            ec2.delete_subnet(SubnetId=subnet_id)
        print("Subnets deleted.")
    except Exception as e:
        print(f"Error deleting subnets: {e}")

    # Delete Security Groups (non-default)
    try:
        print("Deleting security groups...")
        sgs = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['SecurityGroups']
        for sg in sgs:
            if sg['GroupName'] != 'default':
                sg_id = sg['GroupId']
                print(f"Deleting SG: {sg_id}")
                ec2.delete_security_group(GroupId=sg_id)
        print("Security groups deleted.")
    except Exception as e:
        print(f"Error deleting security groups: {e}")

    # Finally, delete the VPC
    try:
        print(f"Attempting to delete VPC: {vpc_id}")
        ec2.delete_vpc(VpcId=vpc_id)
        print(f"VPC {vpc_id} successfully deleted.")
    except Exception as e:
        print(f"Could not delete VPC {vpc_id}. It might have remaining dependencies or is already deleted. Error: {e}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python cleanup.py <VPC_ID> <REGION>")
        sys.exit(1)
    
    vpc_to_delete = sys.argv[1]
    aws_region = sys.argv[2]
    cleanup_vpc(vpc_to_delete, aws_region) 