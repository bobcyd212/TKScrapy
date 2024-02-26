# CreateTime: 2024/2/25
# Author: Tabby Cat
import pandas as pd
import datetime
from TikTokApi import TikTokApi
import asyncio
import constants
import argparse

ms_token = constants.MS_TOKEN  # tiktok登陆后可以查询到自己的ms_token
proxy = {"server": constants.PROXY}  # 自己本地的代理服务器地址
month = constants.MONTH  # 需要查询的月份
translation_dict = constants.TRANSLATION_DICT  # 将tiktok返回的对象的key更换为中文
collect_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 数据采集的时间
account_name_list = constants.ACCOUNT_NAMES
print(collect_time)


async def fetch_user_info(api, account_name):
    user = api.user(account_name)
    user_data_dict = await user.info()
    return {
        '账号名称': account_name,
        '粉丝数': user_data_dict["userInfo"]["stats"]["followerCount"],
        '视频数量': user_data_dict["userInfo"]["stats"]["videoCount"]
    }


# 计算结算金额
def calculate_bonus(play_count):
    return 0 if play_count < 1000 else 100 if play_count < 10000 else 150


async def fetch_video_data(account_name, video):
    video_id = video.id
    video_url = f'https://www.tiktok.com/@{account_name}/video/{video_id}'
    create_time = datetime.datetime.utcfromtimestamp(video.as_dict["createTime"]).strftime('%Y-%m-%d')
    description = video.as_dict["contents"][0]["desc"]
    original_dict = video.as_dict["stats"]
    stats = {translation_dict[key]: value for key, value in original_dict.items()}
    play_count = stats["播放"]
    return {
        '创建时间': create_time,
        '视频标题': description,
        '视频链接': video_url,
        '播放数据': play_count,
        '点赞数据': stats["点赞"],
        '分享数据': stats["分享"],
        '评论数据': stats["评论"],
        '结算金额': calculate_bonus(play_count)

    }


async def user_example(account_name):
    async with TikTokApi() as api:
        await api.create_sessions(ms_tokens=[ms_token], num_sessions=1, proxies=[proxy], sleep_after=3,
                                  override_browser_args=["--incognito"],
                                  headless=False,
                                  )
        try:
            user_data = await fetch_user_info(api, account_name)
            print(user_data)
            user = api.user(account_name)
            videos_data = []
            async for video in user.videos(count=30):
                video_data = await fetch_video_data(account_name, video)
                if video_data['创建时间'].startswith(month):
                    videos_data.append(video_data)
        except Exception as e:
            print(f"处理用户{account_name}时出现错误: {e}")

        df_videos = pd.DataFrame(videos_data)
        filename = f'{account_name}_{month}.xlsx'
        writer = pd.ExcelWriter(filename, engine='openpyxl')
        df_collect_time = pd.DataFrame([{'数据采集时间': collect_time}])
        df_collect_time.to_excel(writer, index=False, startrow=0)
        df_user = pd.DataFrame([user_data])
        df_user.to_excel(writer, index=False, startrow=2)
        df_videos.to_excel(writer, index=False, startrow=4)
        # 保存Excel文件
        writer.close()


# 可以在运行脚本时通过命令行参数--accounts指定一个或多个账号名称
def get_args():
    parser = argparse.ArgumentParser(description='Fetch TikTok account data.')
    parser.add_argument('--accounts', nargs='+', help='List of account names to fetch data for', default=[])
    return parser.parse_args()


# 没有指定任何账号，脚本将默认查询设置的多个账号的数据
async def main():
    args = get_args()
    account_names = args.accounts if args.accounts else account_name_list
    tasks = [user_example(account_name) for account_name in account_names]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
