#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Connection Limits Test Script
测试数据库连接限制的脚本
"""

from DBpool import DBpool
import pymysql

def test_connection_limits():
    """测试不同连接数的创建情况"""
    
    # 数据库连接参数
    host = 'testapi.fuhu.tech'
    port = 3306
    user = 'ai_creator'
    password = 'ai_creator123456'
    db = 'esports'
    
    # 测试不同的连接数
    test_sizes = [5, 10, 20, 50, 100]
    
    for max_conn in test_sizes:
        print(f"\n{'='*50}")
        print(f"Testing with {max_conn} connections")
        print(f"{'='*50}")
        
        try:
            # 创建连接池
            pool = DBpool(
                max_connections=max_conn,
                host=host,
                port=port,
                user=user,
                password=password,
                db=db,
                cursorclass='DictCursor'
            )
            
            # 检查MySQL限制
            pool.check_mysql_limits()
            
            # 获取实际创建的连接数
            actual_size = pool.get_pool_size()
            print(f"Successfully created {actual_size} connections")
            
            # 关闭连接池
            pool.close()
            print(f"Connection pool with {max_conn} connections: SUCCESS")
            
        except Exception as e:
            print(f"Connection pool with {max_conn} connections: FAILED")
            print(f"Error: {str(e)}")
            
            # 如果连接池创建失败，尝试检查MySQL状态
            try:
                single_conn = pymysql.connect(
                    host=host, port=port, user=user, 
                    password=password, db=db
                )
                with single_conn.cursor() as cursor:
                    cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
                    result = cursor.fetchone()
                    print(f"MySQL max_connections: {result[1] if result else 'Unknown'}")
                single_conn.close()
            except Exception as e2:
                print(f"Cannot connect to MySQL: {e2}")

def check_mysql_directly():
    """直接检查MySQL连接限制"""
    print(f"\n{'='*50}")
    print("Checking MySQL connection limits directly")
    print(f"{'='*50}")
    
    try:
        conn = pymysql.connect(
            host='testapi.fuhu.tech',
            port=3306,
            user='ai_creator',
            password='ai_creator123456',
            db='esports'
        )
        
        with conn.cursor() as cursor:
            # 检查最大连接数
            cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
            result = cursor.fetchone()
            print(f"Max connections: {result[1] if result else 'Unknown'}")
            
            # 检查当前连接数
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cursor.fetchone()
            print(f"Current connections: {result[1] if result else 'Unknown'}")
            
            # 检查最大使用过的连接数
            cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
            result = cursor.fetchone()
            print(f"Max used connections: {result[1] if result else 'Unknown'}")
            
            # 检查其他相关限制
            cursor.execute("SHOW VARIABLES LIKE 'max_user_connections'")
            result = cursor.fetchone()
            print(f"Max user connections: {result[1] if result else 'Unlimited'}")
            
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")

if __name__ == '__main__':
    print("Database Connection Limits Diagnostic Tool")
    print("数据库连接限制诊断工具")
    
    # 首先直接检查MySQL状态
    check_mysql_directly()
    
    # 然后测试不同大小的连接池
    test_connection_limits()
    
    print(f"\n{'='*50}")
    print("Diagnostic completed")
    print("诊断完成")
    print(f"{'='*50}")
