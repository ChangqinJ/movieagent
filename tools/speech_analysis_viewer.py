#!/usr/bin/env python3
"""
Speech Analysis Viewer - 查看和分析保存的语音分析结果

使用方法:
1. 查看某个工作目录的语音分析汇总:
   python tools/speech_analysis_viewer.py --working-dir .working_dir/6

2. 查看特定shot的详细分析:
   python tools/speech_analysis_viewer.py --shot-analysis .working_dir/6/shots/0_video_speech_analysis.json

3. 导出时间轴到CSV:
   python tools/speech_analysis_viewer.py --working-dir .working_dir/6 --export-csv timeline.csv
"""

import os
import json
import argparse
import csv
from typing import Dict, List, Optional
from datetime import datetime


class SpeechAnalysisViewer:
    """查看和处理语音分析结果的工具"""
    
    def __init__(self):
        pass
    
    def view_summary(self, working_dir: str) -> Optional[Dict]:
        """查看语音分析汇总"""
        shots_dir = os.path.join(working_dir, "shots")
        summary_path = os.path.join(shots_dir, "speech_analysis_summary.json")
        
        if not os.path.exists(summary_path):
            print(f"❌ 找不到语音分析汇总文件: {summary_path}")
            return None
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            
            print("=" * 60)
            print("🎬 语音分析汇总报告")
            print("=" * 60)
            print(f"📅 分析时间: {summary.get('analysis_timestamp', 'Unknown')}")
            print(f"🎥 总shot数: {summary.get('total_shots', 0)}")
            print(f"🗣️ 总语音段数: {summary.get('total_speech_segments', 0)}")
            print()
            
            shots_analyzed = summary.get('shots_analyzed', [])
            for i, shot in enumerate(shots_analyzed):
                print(f"Shot {i}:")
                print(f"  📁 文件: {os.path.basename(shot.get('video_path', ''))}")
                print(f"  🗣️ 语音段数: {shot.get('speech_segments_count', 0)}")
                
                # 显示语音段详情
                speech_segments = shot.get('speech_segments', [])
                for j, segment in enumerate(speech_segments):
                    start_time = segment.get('start_time', 0)
                    end_time = segment.get('end_time', 0)
                    speaker = segment.get('speaker', 'Unknown')
                    confidence = segment.get('confidence', 0)
                    print(f"    段 {j+1}: {speaker} | {start_time:.1f}s - {end_time:.1f}s | 置信度: {confidence:.2f}")
                
                if shot.get('analysis_notes'):
                    print(f"  📝 分析注释: {shot['analysis_notes']}")
                print()
            
            return summary
            
        except Exception as e:
            print(f"❌ 读取汇总文件失败: {e}")
            return None
    
    def view_shot_analysis(self, analysis_file_path: str) -> Optional[Dict]:
        """查看特定shot的详细分析"""
        if not os.path.exists(analysis_file_path):
            print(f"❌ 找不到分析文件: {analysis_file_path}")
            return None
        
        try:
            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            print("=" * 60)
            print("🎥 单个Shot语音分析详情")
            print("=" * 60)
            print(f"📁 视频文件: {analysis.get('video_path', 'Unknown')}")
            print()
            
            # 显示原始响应（如果有的话）
            if 'raw_response' in analysis:
                print("🤖 AI模型原始响应:")
                print("-" * 40)
                print(analysis['raw_response'][:500] + "..." if len(analysis['raw_response']) > 500 else analysis['raw_response'])
                print()
            
            # 显示解析结果
            if 'parsed_result' in analysis:
                parsed = analysis['parsed_result']
                print("📊 解析结果:")
                print(f"  说话人: {parsed.get('speaker', 'Unknown')}")
                if 'analysis_notes' in parsed:
                    print(f"  分析注释: {parsed['analysis_notes']}")
                print()
            
            # 显示语音段
            speech_segments = analysis.get('speech_segments', [])
            print(f"🗣️ 语音段详情 (共{len(speech_segments)}段):")
            for i, segment in enumerate(speech_segments):
                start_time = segment.get('start_time', 0)
                end_time = segment.get('end_time', 0)
                speaker = segment.get('speaker', 'Unknown')
                confidence = segment.get('confidence', 0)
                duration = end_time - start_time
                print(f"  段 {i+1}: {speaker}")
                print(f"    ⏰ 时间: {start_time:.1f}s - {end_time:.1f}s (时长: {duration:.1f}s)")
                print(f"    🎯 置信度: {confidence:.2f}")
                print()
            
            return analysis
            
        except Exception as e:
            print(f"❌ 读取分析文件失败: {e}")
            return None
    
    def export_timeline_csv(self, working_dir: str, output_csv: str):
        """导出时间轴到CSV文件"""
        shots_dir = os.path.join(working_dir, "shots")
        summary_path = os.path.join(shots_dir, "speech_analysis_summary.json")
        
        if not os.path.exists(summary_path):
            print(f"❌ 找不到语音分析汇总文件: {summary_path}")
            return
        
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            
            # 准备CSV数据
            csv_data = []
            shots_analyzed = summary.get('shots_analyzed', [])
            
            for shot_idx, shot in enumerate(shots_analyzed):
                video_file = os.path.basename(shot.get('video_path', ''))
                speech_segments = shot.get('speech_segments', [])
                
                for segment_idx, segment in enumerate(speech_segments):
                    csv_data.append({
                        'shot_index': shot_idx,
                        'video_file': video_file,
                        'segment_index': segment_idx,
                        'speaker': segment.get('speaker', 'Unknown'),
                        'start_time': segment.get('start_time', 0),
                        'end_time': segment.get('end_time', 0),
                        'duration': segment.get('end_time', 0) - segment.get('start_time', 0),
                        'confidence': segment.get('confidence', 0)
                    })
            
            # 写入CSV
            if csv_data:
                with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['shot_index', 'video_file', 'segment_index', 'speaker', 
                                'start_time', 'end_time', 'duration', 'confidence']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for row in csv_data:
                        writer.writerow(row)
                
                print(f"✅ 时间轴数据已导出到: {output_csv}")
                print(f"📊 共导出 {len(csv_data)} 条语音段记录")
            else:
                print("❌ 没有找到语音段数据可导出")
                
        except Exception as e:
            print(f"❌ 导出CSV失败: {e}")
    
    def list_available_analyses(self, working_dir: str):
        """列出所有可用的分析文件"""
        shots_dir = os.path.join(working_dir, "shots")
        
        if not os.path.exists(shots_dir):
            print(f"❌ 找不到shots目录: {shots_dir}")
            return
        
        # 查找分析文件
        analysis_files = [f for f in os.listdir(shots_dir) if f.endswith('_speech_analysis.json')]
        summary_file = os.path.join(shots_dir, "speech_analysis_summary.json")
        
        print("=" * 60)
        print("📋 可用的语音分析文件")
        print("=" * 60)
        
        if os.path.exists(summary_file):
            print(f"📊 汇总文件: {summary_file}")
        else:
            print("❌ 未找到汇总文件")
        
        print(f"\n🎥 Shot分析文件 (共{len(analysis_files)}个):")
        for analysis_file in sorted(analysis_files):
            full_path = os.path.join(shots_dir, analysis_file)
            print(f"  - {full_path}")


def main():
    parser = argparse.ArgumentParser(description="语音分析结果查看器")
    parser.add_argument("--working-dir", "-w", help="工作目录路径")
    parser.add_argument("--shot-analysis", "-s", help="查看特定shot的分析文件")
    parser.add_argument("--export-csv", "-c", help="导出时间轴到CSV文件")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有可用的分析文件")
    
    args = parser.parse_args()
    
    viewer = SpeechAnalysisViewer()
    
    if args.shot_analysis:
        # 查看特定shot分析
        viewer.view_shot_analysis(args.shot_analysis)
    
    elif args.working_dir:
        if args.list:
            # 列出可用文件
            viewer.list_available_analyses(args.working_dir)
        elif args.export_csv:
            # 导出CSV
            viewer.export_timeline_csv(args.working_dir, args.export_csv)
        else:
            # 查看汇总
            viewer.view_summary(args.working_dir)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
