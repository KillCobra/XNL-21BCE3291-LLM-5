resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(
    {
      "Name" = var.name
    },
    var.tags
  )
}

resource "aws_subnet" "private" {
  count = length(var.private_subnets)
  
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.azs[count.index]
  
  tags = merge(
    {
      "Name" = format("${var.name}-private-%s", var.azs[count.index])
      "kubernetes.io/role/internal-elb" = "1"
    },
    var.tags
  )
}

resource "aws_subnet" "public" {
  count = length(var.public_subnets)
  
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(
    {
      "Name" = format("${var.name}-public-%s", var.azs[count.index])
      "kubernetes.io/role/elb" = "1"
    },
    var.tags
  )
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  
  tags = merge(
    {
      "Name" = var.name
    },
    var.tags
  )
}

resource "aws_eip" "nat" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.azs)) : 0
  
  vpc = true
  
  tags = merge(
    {
      "Name" = format("${var.name}-%s", var.azs[count.index])
    },
    var.tags
  )
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.azs)) : 0
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = merge(
    {
      "Name" = format("${var.name}-%s", var.azs[count.index])
    },
    var.tags
  )
  
  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "private" {
  count = length(var.private_subnets)
  
  vpc_id = aws_vpc.this.id
  
  tags = merge(
    {
      "Name" = format("${var.name}-private-%s", var.azs[count.index])
    },
    var.tags
  )
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  
  tags = merge(
    {
      "Name" = "${var.name}-public"
    },
    var.tags
  )
}

resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
  
  timeouts {
    create = "5m"
  }
}

resource "aws_route" "private_nat_gateway" {
  count = var.enable_nat_gateway ? length(var.private_subnets) : 0
  
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.single_nat_gateway ? aws_nat_gateway.this[0].id : aws_nat_gateway.this[count.index].id
  
  timeouts {
    create = "5m"
  }
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnets)
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_route_table_association" "public" {
  count = length(var.public_subnets)
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
} 